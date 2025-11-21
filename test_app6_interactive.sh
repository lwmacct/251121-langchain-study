#!/bin/bash
# 测试 app6 交互模式的回车键提交功能

# 模拟用户输入：输入"你好"然后按回车
echo "你好" | timeout 10 uv run python -m apps.app6.main

echo ""
echo "✅ 测试完成"
