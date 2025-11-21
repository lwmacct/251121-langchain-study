"""
App6: 异步聊天应用，基于 app5 界面 + 异步能力

特性：
- ✨ 等待 LLM 响应时可立即输入下一条消息
- 🎨 使用 app5 的界面效果（分割线、行号、提示栏）
- 🚀 异步处理多个请求，响应在下次输入前批量显示
- 📊 实时显示待处理任务数量（"⏳ N 个处理中"）

界面设计（与 app5 相同）：
  ─────────────────────────────────────
  1> 第一行文本
  2> 第二行文本
  ─────────────────────────────────────
  ⏳ 2 个处理中 | Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出

工作流程：
  1. 用户输入消息，按 Enter 提交
  2. 立即显示用户消息，启动后台 LLM 任务
  3. 立即返回输入界面，可以继续输入下一条
  4. 后台任务完成时，响应暂存到 pending_outputs
  5. 下次获取输入前，自动显示所有已完成的响应

技术要点：
- 使用 Application.run_async() 支持异步
- 输出暂存机制避免 Application 运行时输出导致界面错乱
- 完美结合 app5 界面效果和 app6 异步能力
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
    from apps.app6.ui import AsyncChatUI, print_user, print_assistant
else:
    from .config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL, TEMPERATURE, MAX_TOKENS
    from .tools import get_current_time, end_chat
    from .router import route_intent_async, render_history
    from .ui import AsyncChatUI, print_user, print_assistant


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

    # 初始化历史
    history: list = []

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

        # 保留管道模式的历史
        history = session.history

        if not args.interactive:
            return

        # 进入交互模式
        from rich.console import Console
        Console().print("\n[dim]─── 进入交互模式 ───[/dim]\n")

    # 交互模式：使用 app5 界面 + 异步处理
    ui = AsyncChatUI()
    pending_tasks = []

    while True:
        # 获取输入（会先显示所有待输出的响应）
        user_input = await ui.get_input_async()
        if user_input is None:
            break

        # 显示用户消息
        ui.add_pending_output("user", user_input)
        ui.flush_pending_outputs()

        history.append(HumanMessage(content=user_input))

        # 后台处理（不等待）- 使用 default 参数捕获当前输入
        async def process(msg=user_input):
            try:
                action = await route_intent_async(llm, msg, history)

                if action == "time":
                    result = get_current_time.invoke({})
                    reply = f"当前时间：{result}"
                    history.append(AIMessage(content=reply))
                    ui.add_pending_output("assistant", reply, tool_name="get_current_time")

                elif action == "end":
                    result = end_chat.invoke({"reason": user_input})
                    history.append(AIMessage(content=result))
                    ui.add_pending_output("assistant", result, tool_name="end_chat")
                    ui.should_exit = True

                elif action == "summary":
                    sys_msg = SystemMessage(content="用 2-3 句话简洁总结这段对话的主要内容。")
                    human_msg = HumanMessage(content=f"对话内容：\n{render_history(history)}")
                    try:
                        resp = await llm.ainvoke([sys_msg, human_msg])
                        reply = resp.content
                    except Exception as exc:
                        reply = f"总结失败：{exc}"
                    history.append(AIMessage(content=reply))
                    ui.add_pending_output("assistant", reply, tool_name="LLM:summary")

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
                    ui.add_pending_output("assistant", reply, tool_name="LLM:chat")

            finally:
                ui.update_pending(-1)

        # 启动后台任务
        task = asyncio.create_task(process())
        pending_tasks.append(task)
        ui.update_pending(1)

        # 如果用户要退出，等待所有任务完成
        if ui.should_exit:
            for task in pending_tasks:
                await task
            break


def main():
    """入口函数"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
