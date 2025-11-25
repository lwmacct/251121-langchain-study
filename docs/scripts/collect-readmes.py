#!/usr/bin/env -S uv run python
"""
收集项目中的 README.md 文件到 docs/readme 目录

此脚本会：
1. 扫描 apps/ 和 libs/ 目录下的所有 README.md 文件
2. 提取每个 README.md 的标题（第一个 # 标题）
3. 将文件复制到 docs/readme/，文件名使用路径格式（/ 替换为 ~）
4. 在复制的文件顶部添加 YAML frontmatter，包含标题信息
5. 生成 readme-sidebar.json 配置文件供 VitePress 使用
"""

import os
import re
import json
import subprocess
import shutil
from pathlib import Path


def get_project_root() -> Path:
    """获取 git 仓库根目录"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        # 后备方案：使用脚本位置推断（docs/scripts/）
        return Path(__file__).parent.parent.parent


def extract_title(content: str) -> str:
    """从 Markdown 内容中提取第一个 # 标题"""
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled"


def process_readme(readme_path: Path, project_root: Path, output_dir: Path):
    """处理单个 README.md 文件"""
    # 读取内容
    content = readme_path.read_text(encoding='utf-8')

    # 提取标题
    title = extract_title(content)

    # 计算相对路径
    rel_path = readme_path.parent.relative_to(project_root)

    # 生成输出文件名：apps/100-simple-chat-invoke -> apps~100-simple-chat-invoke.md
    output_name = str(rel_path).replace('/', '~') + '.md'
    output_path = output_dir / output_name

    # 检查内容是否已有 frontmatter
    has_frontmatter = content.strip().startswith('---')

    # 构建输出内容
    if not has_frontmatter:
        # 如果没有 frontmatter，添加一个
        frontmatter = f"""---
title: {title}
---

"""
        output_content = frontmatter + content
    else:
        # 如果已有 frontmatter，保持原样
        output_content = content

    # 写入输出文件
    output_path.write_text(output_content, encoding='utf-8')

    print(f"✓ {rel_path} -> {output_name}")
    return output_name


def generate_sidebar_json(collected_items: list[dict], output_dir: Path):
    """生成 sidebar 配置 JSON 文件"""
    # 按类型分组
    apps_items = [item for item in collected_items if item['type'] == 'apps']
    libs_items = [item for item in collected_items if item['type'] == 'libs']

    # 构建 sidebar 结构
    sidebar_sections = []

    if apps_items:
        sidebar_sections.append({
            "text": "应用示例",
            "items": [
                {"text": item['title'], "link": item['link']}
                for item in sorted(apps_items, key=lambda x: x['filename'])
            ]
        })

    if libs_items:
        sidebar_sections.append({
            "text": "库模块",
            "items": [
                {"text": item['title'], "link": item['link']}
                for item in sorted(libs_items, key=lambda x: x['filename'])
            ]
        })

    # 写入 JSON 文件
    json_path = output_dir / 'readme-sidebar.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(sidebar_sections, f, ensure_ascii=False, indent=2)

    print(f"\n📄 生成配置文件: {json_path.name}")
    return json_path


def main():
    # 确定项目根目录（使用 git 获取）
    project_root = get_project_root()

    # 确定输出目录
    output_dir = project_root / 'docs' / 'readme'

    # 清空输出目录（删除所有旧文件，避免残留）
    if output_dir.exists():
        print(f"🗑️  清空输出目录: {output_dir.relative_to(project_root)}\n")
        shutil.rmtree(output_dir)

    # 重新创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 扫描目标目录
    target_dirs = ['apps', 'libs']
    collected_items = []

    print("🔍 扫描 README.md 文件...\n")

    for target_dir in target_dirs:
        target_path = project_root / target_dir
        if not target_path.exists():
            print(f"⚠️  目录不存在: {target_dir}")
            continue

        # 查找所有 README.md 文件
        for readme_path in target_path.rglob('README.md'):
            # 跳过 node_modules、.venv 等目录
            if any(part.startswith('.') or part in ['node_modules', 'dist', 'build']
                   for part in readme_path.parts):
                continue

            try:
                # 读取内容并提取标题
                content = readme_path.read_text(encoding='utf-8')
                title = extract_title(content)

                # 验证：跳过空文件或没有有效标题的文件
                if not content.strip():
                    rel_path = readme_path.parent.relative_to(project_root)
                    print(f"⊘ {rel_path} -> 跳过（文件为空）")
                    continue

                if title == "Untitled":
                    rel_path = readme_path.parent.relative_to(project_root)
                    print(f"⊘ {rel_path} -> 跳过（没有找到标题）")
                    continue

                # 计算相对路径和输出文件名
                rel_path = readme_path.parent.relative_to(project_root)
                output_name = str(rel_path).replace('/', '~') + '.md'
                output_path = output_dir / output_name

                # 构建输出内容
                has_frontmatter = content.strip().startswith('---')
                if not has_frontmatter:
                    frontmatter = f"""---
title: {title}
---

"""
                    output_content = frontmatter + content
                else:
                    output_content = content

                # 写入输出文件
                output_path.write_text(output_content, encoding='utf-8')

                # 收集元数据
                collected_items.append({
                    'type': target_dir,  # 'apps' or 'libs'
                    'filename': output_name,
                    'title': title,
                    'link': f'/readme/{output_name.replace(".md", "")}'
                })

                print(f"✓ {rel_path} -> {output_name}")
            except Exception as e:
                print(f"✗ 处理失败 {readme_path}: {e}")

    print(f"\n✅ 完成！共收集 {len(collected_items)} 个 README 文件到 docs/readme/")

    # 生成 sidebar JSON 配置
    if collected_items:
        generate_sidebar_json(collected_items, output_dir)

        # 显示收集的文件列表
        print("\n📋 收集的文件:")
        for item in sorted(collected_items, key=lambda x: x['filename']):
            print(f"   - {item['filename']}")


if __name__ == '__main__':
    main()
