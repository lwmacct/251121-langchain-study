"""App6: 优化的聊天应用

核心优化：
1. 使用 LangChain bind_tools 让 LLM 自动决定工具调用，消除手动路由
2. 统一的 Agent.chat() 接口处理所有类型的交互
3. 清晰的模块分离：Agent (AI逻辑) + Session (状态) + UI (交互)
4. 更好的可扩展性和可维护性

对比 app5:
- app5: 手动路由 (LLM判断意图) -> 分支处理 (if time/chat/summary/end)
- app6: Agent.chat() -> 自动工具调用 -> 统一返回

演示场景：
- "现在几点" -> LLM 自动调用 get_current_time 工具
- "是上午还是下午" -> LLM 先调用 get_current_time，再基于结果推理
- "2 + 3 * 4" -> LLM 自动调用 calculate 工具
- "你好" -> LLM 直接回答，无需工具
"""

import argparse
import os
import sys

# 添加当前目录到 sys.path，支持同目录导入
sys.path.insert(0, os.path.dirname(__file__))

from agent import create_agent
from session import Session
from ui import (
    print_user,
    print_assistant,
    print_system,
    print_error,
    get_input_iterator,
    get_advanced_input_iterator,
    ADVANCED_UI_AVAILABLE,
)
from config import config


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="App6: 优化的聊天应用（基于 LangChain bind_tools）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python -m apps.app6                          # 交互模式
  python -m apps.app6 --simple                 # 简化输入模式
  echo "现在几点" | python -m apps.app6        # 管道模式
  echo "2 + 3 * 4" | python -m apps.app6 -i   # 管道 + 交互模式
        """,
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="管道结束后进入交互模式",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="使用简化输入模式（不使用 prompt_toolkit）",
    )
    return parser.parse_args()


def main():
    """主函数 - 优化后的简洁实现"""
    args = parse_args()

    # 打印欢迎信息
    if config.debug:
        print_system(f"调试模式已启用 | 模型: {config.model}")

    # 初始化组件
    agent = create_agent()
    session = Session()

    # 选择输入模式
    if args.simple or not ADVANCED_UI_AVAILABLE:
        input_iterator = get_input_iterator(interactive_after_pipe=args.interactive)
    else:
        input_iterator = get_advanced_input_iterator(
            interactive_after_pipe=args.interactive
        )

    # 主循环 - 简洁统一的处理流程
    try:
        for user_input, from_pipe in input_iterator:
            # 1. 打印用户输入（如果来自管道）
            if from_pipe:
                print_user(user_input)

            # 2. 添加到历史
            session.add_user_message(user_input)

            # 3. 调用 Agent - 统一入口，自动处理工具调用
            try:
                reply, tool_calls = agent.chat(user_input, session.get_history()[:-1])

                # 4. 添加回复到历史
                session.add_assistant_message(reply)

                # 5. 打印助手回复
                print_assistant(reply, tool_calls)

            except KeyboardInterrupt:
                print_system("操作已取消")
                continue
            except Exception as e:
                error_msg = f"处理失败：{e}"
                print_error(error_msg)
                session.add_assistant_message(f"[错误] {error_msg}")

    except KeyboardInterrupt:
        print_system("\n会话已中断")

    # 会话结束统计
    if config.debug and session.get_message_count() > 0:
        print_system(f"\n会话统计: {session.get_message_count()} 条消息")


if __name__ == "__main__":
    main()
