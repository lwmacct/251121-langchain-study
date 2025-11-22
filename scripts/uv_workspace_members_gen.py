#!/usr/bin/env python3
"""
自动生成 uv 工作区成员的脚本。
扫描 libs/ 和 apps/ 目录并更新 pyproject.toml
"""

from pathlib import Path
import sys
import re


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


def format_members_toml(members: list[str]) -> str:
    """将成员列表格式化为 TOML 数组。"""
    if not members:
        return "members = []"

    lines = ["members = ["]
    lines.extend(f'  "{member}",' for member in members)
    lines.append("]")
    return "\n".join(lines)


def update_pyproject_toml(pyproject_path: Path, members: list[str]) -> None:
    """
    更新 pyproject.toml 中的工作区成员。

    策略：查找 [tool.uv.workspace] 部分并替换整个部分的内容。
    """
    content = pyproject_path.read_text(encoding="utf-8")

    # 匹配整个 [tool.uv.workspace] 部分的模式
    # 从 [tool.uv.workspace] 匹配到下一个部分或文件末尾
    pattern = re.compile(
        r"(\[tool\.uv\.workspace\])\s*\n"  # 部分标题
        r"(?:.*?\n)*?"  # 任意内容（非贪婪）
        r"(?=\n\[|\Z)",  # 直到下一个部分或结尾
        re.MULTILINE,
    )

    new_section = f"[tool.uv.workspace]\n{format_members_toml(members)}\n"

    # 如果部分存在则替换
    new_content, count = pattern.subn(new_section, content)

    # 如果部分不存在，则追加
    if count == 0:
        new_content = content.rstrip() + f"\n\n{new_section}"

    pyproject_path.write_text(new_content, encoding="utf-8")


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


if __name__ == "__main__":
    main()
