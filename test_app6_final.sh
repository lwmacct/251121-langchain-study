#!/bin/bash
# App6 综合测试脚本

echo "========================================="
echo "App6 功能测试 (uv run apps/app6/main.py)"
echo "========================================="

echo -e "\n[测试 1] 工具调用 - 获取时间"
echo "现在几点" | uv run apps/app6/main.py --simple

echo -e "\n[测试 2] 工具调用 - 数学计算"
echo "计算 15 * 8 + 7" | uv run apps/app6/main.py --simple

echo -e "\n[测试 3] 普通对话"
echo "你好，介绍一下自己" | uv run apps/app6/main.py --simple

echo -e "\n[测试 4] 多轮对话（管道模式）"
echo -e "现在几点\n是上午还是下午\n2的10次方是多少" | uv run apps/app6/main.py --simple

echo -e "\n[测试 5] 调试模式"
echo "现在几点" | APP6_DEBUG=1 uv run apps/app6/main.py --simple

echo -e "\n========================================="
echo "✅ 所有测试完成！"
echo "========================================="
