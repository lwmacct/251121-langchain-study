"""
App5: 简单聊天应用，演示工具调用和 LLM 回答

- "现在几点" -> 工具调用 (get_current_time)
- "是下午还是上午" -> LLM 回答
- "总结对话" -> LLM 回答
- "结束聊天" -> 工具调用 (end_chat)
"""

import argparse
import sys

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 支持直接运行和模块运行两种方式
if __name__ == "__main__" and __package__ is None:
    # 直接运行：python apps/app5/main.py
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from apps.app5.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL, TEMPERATURE, MAX_TOKENS
    from apps.app5.tools import get_current_time, end_chat
    from apps.app5.router import route_intent, render_history
    from apps.app5.ui import get_input_iterator, print_user, print_assistant
else:
    # 模块运行：python -m apps.app5
    from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL, TEMPERATURE, MAX_TOKENS
    from .tools import get_current_time, end_chat
    from .router import route_intent, render_history
    from .ui import get_input_iterator, print_user, print_assistant


def parse_args():
    parser = argparse.ArgumentParser(description="App5: 聊天应用")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="管道结束后进入交互模式")
    return parser.parse_args()


def main():
    args = parse_args()

    llm = ChatOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    history: list = []

    for user_input, from_pipe in get_input_iterator(interactive_after_pipe=args.interactive):
        if from_pipe:
            print_user(user_input)  # 管道输入需要打印

        history.append(HumanMessage(content=user_input))
        action = route_intent(llm, user_input, history)

        if action == "time":
            # 工具调用：获取时间
            result = get_current_time.invoke({})
            reply = f"当前时间：{result}"
            history.append(AIMessage(content=reply))
            print_assistant(reply, tool_name="get_current_time")
            continue

        if action == "end":
            # 工具调用：结束聊天
            result = end_chat.invoke({"reason": user_input})
            history.append(AIMessage(content=result))
            print_assistant(result, tool_name="end_chat")
            sys.exit(0)

        if action == "summary":
            # LLM 回答：总结对话
            sys_msg = SystemMessage(content="用 2-3 句话简洁总结这段对话的主要内容。")
            human_msg = HumanMessage(content=f"对话内容：\n{render_history(history)}")
            try:
                resp = llm.invoke([sys_msg, human_msg])
                reply = resp.content
            except Exception as exc:
                reply = f"总结失败：{exc}"
            history.append(AIMessage(content=reply))
            print_assistant(reply, tool_name="LLM:summary")
            continue

        # action == "chat": LLM 直接回答
        sys_msg = SystemMessage(
            content="你是一个有帮助的中文助手。根据对话上下文回答用户问题。如果用户问时间段（如上午/下午），请基于之前获取的时间信息回答。"
        )
        try:
            resp = llm.invoke([sys_msg] + history)
            reply = resp.content
        except Exception as exc:
            reply = f"回答失败：{exc}"
        history.append(AIMessage(content=reply))
        print_assistant(reply, tool_name="LLM:chat")


if __name__ == "__main__":
    main()
