"""
App6: 异步聊天应用，支持并发输入编辑

特性：
- 等待 LLM 响应时可继续编辑输入
- 异步处理多个请求
- 响应按发送顺序显示
"""

import argparse
import asyncio
import sys
from collections import deque

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 支持直接运行和模块运行两种方式
if __name__ == "__main__" and __package__ is None:
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from apps.app6.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL, TEMPERATURE, MAX_TOKENS
    from apps.app6.tools import get_current_time, end_chat
    from apps.app6.router import route_intent_async, render_history
    from apps.app6.tui import ChatTUI
    from apps.app6.ui import AsyncChatUI, print_user, print_assistant, console
else:
    from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL, TEMPERATURE, MAX_TOKENS
    from .tools import get_current_time, end_chat
    from .router import route_intent_async, render_history
    from .tui import ChatTUI
    from .ui import AsyncChatUI, print_user, print_assistant, console


def parse_args():
    parser = argparse.ArgumentParser(description="App6: 异步聊天应用")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="管道结束后进入交互模式")
    return parser.parse_args()


class AsyncChatSession:
    """异步聊天会话管理器"""

    def __init__(self, llm: ChatOpenAI, ui: AsyncChatUI):
        self.llm = llm
        self.ui = ui
        self.history: list = []
        self.pending_tasks: deque = deque()  # 按顺序存储待处理任务
        self.should_exit = False

    async def process_input(self, user_input: str, from_pipe: bool = False):
        """处理用户输入"""
        if from_pipe:
            print_user(user_input)

        self.history.append(HumanMessage(content=user_input))

        # 创建处理任务
        task = asyncio.create_task(self._handle_response(user_input))
        self.pending_tasks.append(task)
        self.ui.update_pending(1)

    async def _handle_response(self, user_input: str):
        """处理单个响应"""
        try:
            action = await route_intent_async(self.llm, user_input, self.history)

            if action == "time":
                result = get_current_time.invoke({})
                reply = f"当前时间：{result}"
                self.history.append(AIMessage(content=reply))
                print_assistant(reply, tool_name="get_current_time")

            elif action == "end":
                result = end_chat.invoke({"reason": user_input})
                self.history.append(AIMessage(content=result))
                print_assistant(result, tool_name="end_chat")
                self.should_exit = True

            elif action == "summary":
                sys_msg = SystemMessage(content="用 2-3 句话简洁总结这段对话的主要内容。")
                human_msg = HumanMessage(content=f"对话内容：\n{render_history(self.history)}")
                try:
                    resp = await self.llm.ainvoke([sys_msg, human_msg])
                    reply = resp.content
                except Exception as exc:
                    reply = f"总结失败：{exc}"
                self.history.append(AIMessage(content=reply))
                print_assistant(reply, tool_name="LLM:summary")

            else:  # chat
                sys_msg = SystemMessage(
                    content="你是一个有帮助的中文助手。根据对话上下文回答用户问题。如果用户问时间段（如上午/下午），请基于之前获取的时间信息回答。"
                )
                try:
                    resp = await self.llm.ainvoke([sys_msg] + self.history)
                    reply = resp.content
                except Exception as exc:
                    reply = f"回答失败：{exc}"
                self.history.append(AIMessage(content=reply))
                print_assistant(reply, tool_name="LLM:chat")

        finally:
            self.ui.update_pending(-1)

    async def wait_all_pending(self):
        """等待所有待处理任务完成"""
        while self.pending_tasks:
            task = self.pending_tasks.popleft()
            await task


async def async_main():
    """异步主函数"""
    args = parse_args()

    llm = ChatOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    # 处理管道输入
    is_piped = not sys.stdin.isatty()

    if is_piped:
        piped_lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]

        # 管道模式：使用简单输出
        ui = AsyncChatUI()
        session = AsyncChatSession(llm, ui)

        for line in piped_lines:
            await session.process_input(line, from_pipe=True)
            await session.wait_all_pending()
            if session.should_exit:
                return

        if not args.interactive:
            return

        console.print("\n[dim]─── 进入 TUI 模式 ───[/dim]\n")

    # TUI 交互模式
    history: list = []

    async def on_submit(user_input: str):
        """处理用户提交"""
        tui.set_waiting(True)
        tui.add_user_message(user_input)
        history.append(HumanMessage(content=user_input))

        try:
            action = await route_intent_async(llm, user_input, history)

            if action == "time":
                result = get_current_time.invoke({})
                reply = f"当前时间：{result}"
                history.append(AIMessage(content=reply))
                tui.add_assistant_message(reply, tool_name="get_current_time")

            elif action == "end":
                result = end_chat.invoke({"reason": user_input})
                history.append(AIMessage(content=result))
                tui.add_assistant_message(result, tool_name="end_chat")
                tui.exit()

            elif action == "summary":
                sys_msg = SystemMessage(content="用 2-3 句话简洁总结这段对话的主要内容。")
                human_msg = HumanMessage(content=f"对话内容：\n{render_history(history)}")
                try:
                    resp = await llm.ainvoke([sys_msg, human_msg])
                    reply = resp.content
                except Exception as exc:
                    reply = f"总结失败：{exc}"
                history.append(AIMessage(content=reply))
                tui.add_assistant_message(reply, tool_name="LLM:summary")

            else:  # chat
                sys_msg = SystemMessage(
                    content="你是一个有帮助的中文助手。根据对话上下文回答用户问题。"
                )
                try:
                    resp = await llm.ainvoke([sys_msg] + history)
                    reply = resp.content
                except Exception as exc:
                    reply = f"回答失败：{exc}"
                history.append(AIMessage(content=reply))
                tui.add_assistant_message(reply, tool_name="LLM:chat")

        finally:
            tui.set_waiting(False)

    tui = ChatTUI(on_submit=on_submit)
    await tui.run()


def main():
    """入口函数"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
