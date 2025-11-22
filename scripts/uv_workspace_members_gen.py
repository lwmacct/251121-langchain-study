#!/usr/bin/env python3
"""
自动生成 uv 工作区成员的脚本。
扫描 libs/ 和 apps/ 目录并更新 pyproject.toml
"""

from pathlib import Path
import os
import subprocess
import sys


# 确保使用项目 .venv 中的 Python
if not os.environ.get("_VENV_ACTIVATED"):
    try:
        git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
        venv_python = f"{git_root}/.venv/bin/python"
        if os.path.exists(venv_python) and sys.executable != venv_python:
            os.environ["_VENV_ACTIVATED"] = "1"
            os.execv(venv_python, [venv_python] + sys.argv)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

import tomlkit


def detect_toml_indent(content: str) -> int:
    """
    检测 TOML 文件中数组的缩进空格数。

    返回缩进空格数量（如 2 或 4），默认为 2。
    """
    import re

    # 查找数组中的缩进行
    # 匹配类似 '  "foo",' 的行
    pattern = re.compile(r'^(\s+)["\']', re.MULTILINE)
    matches = pattern.findall(content)

    if matches:
        # 返回第一个匹配的缩进长度
        return len(matches[0])

    # 默认使用 2 个空格
    return 2


def find_workspace_members(project_root: Path) -> list[str]:
    """
    查找 libs/ 和 apps/ 中的所有一级目录。

    返回排序后的相对路径列表，如 ['libs/foo', 'apps/bar']。
    """
    return [
        f"{base_dir}/{item.name}"
        for base_dir in ["libs", "apps"]
        if (dir_path := project_root / base_dir).exists()
        for item in sorted(dir_path.iterdir())
        if item.is_dir()
    ]


def update_pyproject_toml(pyproject_path: Path, members: list[str]) -> None:
    """
    使用 tomlkit 更新 pyproject.toml 中的工作区成员。

    优势：保留原有格式、注释和空格。
    """
    content = pyproject_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    # 检测文件的缩进风格（空格数）
    indent_size = detect_toml_indent(content)

    # 确保 [tool.uv.workspace] 段存在
    if "tool" not in doc:
        doc["tool"] = {}
    if "uv" not in doc["tool"]:
        doc["tool"]["uv"] = {}
    if "workspace" not in doc["tool"]["uv"]:
        doc["tool"]["uv"]["workspace"] = {}

    # 创建多行数组格式
    members_array = tomlkit.array()
    members_array.multiline(True)
    for member in members:
        members_array.append(member)

    # 更新 members 列表
    doc["tool"]["uv"]["workspace"]["members"] = members_array

    # 导出时使用检测到的缩进
    output = tomlkit.dumps(doc)

    # tomlkit 默认使用 4 空格，需要替换为检测到的缩进
    if indent_size != 4:
        # 替换数组中的缩进（4 空格 -> 检测到的缩进）
        import re

        target_indent = " " * indent_size
        output = re.sub(r"^(    )", target_indent, output, flags=re.MULTILINE)

    pyproject_path.write_text(output, encoding="utf-8")


def update_member_project_name(member_path: Path, project_name: str) -> bool:
    """
    使用 tomlkit 更新成员项目的 pyproject.toml 中的 [project] name。

    Args:
        member_path: 成员目录的路径
        project_name: 要设置的项目名称（通常是目录名）

    Returns:
        bool: 是否成功更新（如果名称已正确则返回 False）
    """
    pyproject_path = member_path / "pyproject.toml"

    if not pyproject_path.exists():
        return False

    content = pyproject_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    # 检查 [project] 段是否存在
    if "project" not in doc:
        return False

    # 检查 name 字段是否存在
    if "name" not in doc["project"]:
        return False

    # 如果名称已经正确，则跳过
    current_name = doc["project"]["name"]
    if current_name == project_name:
        return False

    # 更新名称
    doc["project"]["name"] = project_name

    pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return True


def main():
    """主入口函数。"""
    # 获取路径
    project_root = Path(__file__).resolve().parent.parent
    pyproject_path = project_root / "pyproject.toml"

    # 验证
    if not pyproject_path.exists():
        print(f"✗ Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    # 查找成员
    members = find_workspace_members(project_root)

    if not members:
        print("⚠ Warning: No directories found in libs/ or apps/")
        sys.exit(0)

    # 更新文件
    update_pyproject_toml(pyproject_path, members)

    # 报告结果
    print("✓ Successfully updated workspace members in pyproject.toml")
    print(f"  Found {len(members)} member(s):")
    for member in members:
        print(f"    - {member}")

    # 更新所有成员项目的 [project] name
    print("\n📝 Updating [project] name for all members...")
    updated_count = 0
    skipped_count = 0

    for member in members:
        member_path = project_root / member
        project_name = member_path.name  # 使用目录名作为项目名

        if update_member_project_name(member_path, project_name):
            print(f'  ✓ Updated {member} → name = "{project_name}"')
            updated_count += 1
        else:
            skipped_count += 1

    # 报告更新结果
    if updated_count > 0:
        print(f"\n✓ Updated {updated_count} project name(s)")
    if skipped_count > 0:
        print(f"  ℹ Skipped {skipped_count} (already correct or no pyproject.toml)")


if __name__ == "__main__":
    main()
