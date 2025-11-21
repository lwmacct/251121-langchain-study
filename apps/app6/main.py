"""
App6: 异步聊天应用，底部固定输入区 + 上方滚动输出

特性：
- ✨ 等待 LLM 响应时可立即输入下一条消息
- 📜 上方使用标准终端输出（Rich print），自然滚动
- 📝 底部固定输入框（prompt_toolkit Application）
- ⚡ 后台任务完成后在下次输入前显示（避免视觉冲突）
- 📊 实时显示待处理任务数量

界面设计：
  用户: 你好                          ↑ 终端滚动区域
  助手: [LLM:chat] 你好！...          ↑ Rich print 输出
  用户: 现在几点                      ↑ 自然向上滚动
  助手: [get_current_time] 23:00      ↑
  ─────────────────────────────────  ← 分割线
  1> 输入内容...                      ← 固定在底部
  ─────────────────────────────────  ← 分割线
  ⏳ 2 个处理中 | Ctrl+J 换行 | Enter 发送

工作流程：
  1. 循环开始：显示所有已完成任务的输出（Rich print）
  2. 启动 Application 获取输入（固定在底部）
  3. 用户输入完成，Application 退出
  4. 显示用户消息，启动后台任务
  5. 回到步骤 1（后台任务在运行，但不阻塞输入循环）

技术要点：
- 输出总是在 Application 不运行时进行
- Application 仅用于获取输入，固定在底部
- 输出使用 Rich print，自然向上滚动
- 完美实现"上方滚动 + 底部固定"的效果
"""

import argparse
import asyncio
import sys

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

        # 管道模式：同步处理每条消息
        for line in piped_lines:
            print_user(line)
            history.append(HumanMessage(content=line))

            action = await route_intent_async(llm, line, history)

            if action == "time":
                result = get_current_time.invoke({})
                reply = f"当前时间：{result}"
                history.append(AIMessage(content=reply))
                print_assistant(reply, tool_name="get_current_time")

            elif action == "end":
                result = end_chat.invoke({"reason": line})
                history.append(AIMessage(content=result))
                print_assistant(result, tool_name="end_chat")
                return

            elif action == "summary":
                sys_msg = SystemMessage(content="用 2-3 句话简洁总结这段对话的主要内容。")
                human_msg = HumanMessage(content=f"对话内容：\n{render_history(history)}")
                try:
                    resp = await llm.ainvoke([sys_msg, human_msg])
                    reply = resp.content
                except Exception as exc:
                    reply = f"总结失败：{exc}"
                history.append(AIMessage(content=reply))
                print_assistant(reply, tool_name="LLM:summary")

            else:  # chat
                sys_msg = SystemMessage(
                    content="你是一个有帮助的中文助手。根据对话上下文回答用户问题。如果用户问时间段（如上午/下午），请基于之前获取的时间信息回答。"
                )
                try:
                    resp = await llm.ainvoke([sys_msg] + history)
                    reply = resp.content
                except Exception as exc:
                    reply = f"回答失败：{exc}"
                history.append(AIMessage(content=reply))
                print_assistant(reply, tool_name="LLM:chat")

        if not args.interactive:
            return

    # 交互模式：底部固定输入区 + 上方滚动输出
    ui = AsyncChatUI()
    pending_tasks = {}
    task_counter = 0
    pending_outputs = []  # 待输出的消息队列
    should_exit = False

    async def process_message(msg: str):
        """后台处理消息，完成时添加到输出队列"""
        try:
            action = await route_intent_async(llm, msg, history)

            if action == "time":
                result = get_current_time.invoke({})
                reply = f"当前时间：{result}"
                history.append(AIMessage(content=reply))
                pending_outputs.append(("assistant", reply, "get_current_time"))

            elif action == "end":
                result = end_chat.invoke({"reason": msg})
                history.append(AIMessage(content=result))
                pending_outputs.append(("assistant", result, "end_chat"))
                nonlocal should_exit
                should_exit = True

            elif action == "summary":
                sys_msg = SystemMessage(content="用 2-3 句话简洁总结这段对话的主要内容。")
                human_msg = HumanMessage(content=f"对话内容：\n{render_history(history)}")
                try:
                    resp = await llm.ainvoke([sys_msg, human_msg])
                    reply = resp.content
                except Exception as exc:
                    reply = f"总结失败：{exc}"
                history.append(AIMessage(content=reply))
                pending_outputs.append(("assistant", reply, "LLM:summary"))

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
                pending_outputs.append(("assistant", reply, "LLM:chat"))

        except Exception as e:
            pending_outputs.append(("assistant", f"错误: {e}", "Error"))

    while not should_exit:
        # 1. 等待并显示所有已完成的任务输出
        done_ids = [tid for tid, task in pending_tasks.items() if task.done()]
        for tid in done_ids:
            task = pending_tasks.pop(tid)
            try:
                await task
            except Exception:
                pass

        # 2. 显示所有待输出的消息（在 Application 运行前）
        while pending_outputs:
            output_type, content, tool_name = pending_outputs.pop(0)
            if output_type == "assistant":
                print_assistant(content, tool_name)

        # 3. 更新待处理计数
        ui.pending_count = len(pending_tasks)

        # 4. 获取用户输入（Application 运行）
        user_input = await ui.get_input_async()
        if user_input is None:
            break

        # 5. 显示用户消息（Application 退出后）
        print_user(user_input)
        history.append(HumanMessage(content=user_input))

        # 6. 启动后台任务
        task_counter += 1
        task = asyncio.create_task(process_message(user_input))
        pending_tasks[task_counter] = task

    # 等待所有任务完成
    for task in list(pending_tasks.values()):
        if not task.done():
            await task

    # 显示剩余输出
    while pending_outputs:
        output_type, content, tool_name = pending_outputs.pop(0)
        if output_type == "assistant":
            print_assistant(content, tool_name)


def main():
    """入口函数"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
