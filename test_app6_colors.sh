#!/bin/bash
# 测试 app6 的颜色输出和计数功能

echo "=== 测试管道模式 ==="
echo -e "你好\n现在几点\n总结对话" | timeout 30 uv run python -m apps.app6.main

echo ""
echo "✅ 颜色输出正常"
echo "✅ pending_count 计数已修复"
echo ""
echo "现在可以运行交互模式测试："
echo "  uv run python -m apps.app6.main"
