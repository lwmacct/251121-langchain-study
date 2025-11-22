#!/usr/bin/env python3
"""
Script to automatically generate uv workspace members.
Scans libs/ and apps/ directories and updates pyproject.toml
"""

from pathlib import Path
import sys
import re


def find_workspace_members(project_root: Path) -> list[str]:
    """
    Find all first-level directories in libs/ and apps/.

    Returns a sorted list of relative paths like ['libs/foo', 'apps/bar'].
    """
    return [
        f"{base_dir}/{item.name}"
        for base_dir in ["libs", "apps"]
        if (dir_path := project_root / base_dir).exists()
        for item in sorted(dir_path.iterdir())
        if item.is_dir()
    ]


def format_members_toml(members: list[str]) -> str:
    """Format members as TOML array."""
    if not members:
        return "members = []"

    lines = ["members = ["]
    lines.extend(f'  "{member}",' for member in members)
    lines.append("]")
    return "\n".join(lines)


def update_pyproject_toml(pyproject_path: Path, members: list[str]) -> None:
    """
    Update workspace members in pyproject.toml.

    Strategy: Find [tool.uv.workspace] section and replace entire section content.
    """
    content = pyproject_path.read_text(encoding="utf-8")

    # Pattern to match the entire [tool.uv.workspace] section
    # This matches from [tool.uv.workspace] to the next section or EOF
    pattern = re.compile(
        r"(\[tool\.uv\.workspace\])\s*\n"  # Section header
        r"(?:.*?\n)*?"  # Any content (non-greedy)
        r"(?=\n\[|\Z)",  # Until next section or end
        re.MULTILINE,
    )

    new_section = f"[tool.uv.workspace]\n{format_members_toml(members)}\n"

    # Replace the section if it exists
    new_content, count = pattern.subn(new_section, content)

    # If section doesn't exist, append it
    if count == 0:
        new_content = content.rstrip() + f"\n\n{new_section}"

    pyproject_path.write_text(new_content, encoding="utf-8")


def main():
    """Main entry point."""
    # Get paths
    project_root = Path(__file__).resolve().parent.parent
    pyproject_path = project_root / "pyproject.toml"

    # Validate
    if not pyproject_path.exists():
        print(f"✗ Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    # Find members
    members = find_workspace_members(project_root)

    if not members:
        print("⚠ Warning: No directories found in libs/ or apps/")
        sys.exit(0)

    # Update file
    update_pyproject_toml(pyproject_path, members)

    # Report
    print("✓ Successfully updated workspace members in pyproject.toml")
    print(f"  Found {len(members)} member(s):")
    for member in members:
        print(f"    - {member}")


if __name__ == "__main__":
    main()
