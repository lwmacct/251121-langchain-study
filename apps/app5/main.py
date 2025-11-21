"""
App5: 简单聊天应用，演示工具调用和 LLM 回答

- "现在几点" -> 工具调用 (get_current_time)
- "是下午还是上午" -> LLM 回答
- "总结对话" -> LLM 回答
- "结束聊天" -> 工具调用 (end_chat)
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from rich.console import Console
from rich.text import Text
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, BufferControl, Dimension
from prompt_toolkit.lexers import SimpleLexer
import shutil

import argparse

DEBUG = os.getenv("APP5_DEBUG") == "1"
console = Console()

def parse_args():
    parser = argparse.ArgumentParser(description="App5: 聊天应用")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="管道结束后进入交互模式")
    return parser.parse_args()

# OpenRouter 配置
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = "anthropic/claude-3.5-sonnet"


@tool
def get_current_time() -> str:
    """获取当前时间，返回 UTC 和北京时间"""
    utc_now = datetime.now(timezone.utc)
    beijing = utc_now.astimezone(timezone(timedelta(hours=8)))
    return f"UTC: {utc_now.strftime('%H:%M:%S')} | 北京时间: {beijing.strftime('%H:%M:%S')}"


@tool
def end_chat(reason: str = "用户请求") -> str:
    """结束聊天会话"""
    return f"会话结束。原因：{reason}。再见！"


class RouteDecision(BaseModel):
    """路由决策"""

    action: Literal["time", "chat", "summary", "end"]
    reason: Optional[str] = None


def log_debug(title: str, content: str, style: str = "dim"):
    """DEBUG 模式下输出调试信息"""
    if DEBUG:
        console.print(f"[{style}]┌─ {title}[/{style}]")
        for line in content.split("\n"):
            console.print(f"[{style}]│ {line}[/{style}]")
        console.print(f"[{style}]└{'─' * 40}[/{style}]")


def route_intent(llm: ChatOpenAI, user_text: str, history: list) -> str:
    """使用 LLM 判断用户意图"""
    import json
    import re

    sys_msg = SystemMessage(
        content="""你是意图路由器。分析用户输入，返回一个 JSON 对象。

规则：
- time: 仅当用户询问"本地当前时间"时使用（如"现在几点"、"几点了"）
- chat: 需要 LLM 思考回答的问题（如其他时区时间、判断上午下午、解释概念等）
- summary: 用户要求总结对话
- end: 用户要结束对话（再见、退出、结束聊天）

返回格式：{"action": "time|chat|summary|end", "reason": "简短理由"}

示例：
- "现在几点" -> {"action": "time", "reason": "询问本地时间"}
- "美国现在几点" -> {"action": "chat", "reason": "需要计算其他时区"}
- "是上午还是下午" -> {"action": "chat", "reason": "需要判断时间段"}
- "总结对话" -> {"action": "summary", "reason": "用户要求总结"}
- "再见" -> {"action": "end", "reason": "用户要结束"}"""
    )
    human_msg = HumanMessage(content=f"用户输入：{user_text}\n\n请返回 JSON：")

    try:
        resp = llm.invoke([sys_msg, human_msg])
        content = resp.content.strip()
        # 提取 JSON
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            data = json.loads(json_match.group())
            action = data.get("action", "chat")
            reason = data.get("reason", "")
            if action in ["time", "chat", "summary", "end"]:
                log_debug("路由决策 (LLM)", f"action: {action}\nreason: {reason}", "cyan")
                return action
    except Exception as exc:
        log_debug("路由错误", str(exc), "red")

    # 关键词兜底（更保守）
    lower = user_text.lower()
    action = "chat"
    # 只有非常明确的情况才用关键词
    if user_text in ["现在几点", "几点了", "现在时间"]:
        action = "time"
    elif any(k in lower for k in ["总结对话", "概括一下"]):
        action = "summary"
    elif any(k in lower for k in ["结束聊天", "退出", "bye", "再见"]):
        action = "end"

    # 关键词兜底是降级方案，需要明显警告
    console.print("[bold red on yellow]⚠️  警告: LLM 路由失败，使用关键词兜底！[/bold red on yellow]")
    log_debug("路由决策 (关键词兜底)", f"action: {action}", "yellow")
    return action


def render_history(history: list, limit: int = 10) -> str:
    """渲染历史对话"""
    lines = []
    for msg in history[-limit:]:
        if isinstance(msg, HumanMessage):
            lines.append(f"用户: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"助手: {msg.content}")
    return "\n".join(lines)


def print_user(content: str):
    """打印用户消息"""
    console.print(Text("用户: ", style="bold green") + Text(content))


def print_assistant(content: str, tool_name: str | None = None):
    """打印助手消息"""
    if tool_name:
        tag = Text(f"[{tool_name}] ", style="bold magenta")
        console.print(Text("助手: ", style="bold blue") + tag + Text(content))
    else:
        console.print(Text("助手: ", style="bold blue") + Text(content))


def get_input_iterator(interactive_after_pipe: bool = False):
    """获取输入迭代器，支持管道和交互式模式

    Args:
        interactive_after_pipe: 管道结束后是否进入交互模式 (-i 参数)

    Yields:
        (user_input, from_pipe): 用户输入和是否来自管道
    """
    is_piped = not sys.stdin.isatty()

    if is_piped:
        # 管道模式：先处理管道内容
        piped_lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
        for line in piped_lines:
            yield line, True  # 来自管道，需要打印

        # 管道结束后，根据 -i 参数决定是否进入交互模式
        if not interactive_after_pipe:
            return

        console.print("\n[dim]─── 进入交互模式 (连按两次 Ctrl+C 退出) ───[/dim]\n")

    # 交互式模式 - 使用 prompt_toolkit Application 提供动态高度输入框
    last_ctrl_c_time = 0
    hint_text = [" Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"]
    result_text = [None]  # 用于存储用户输入结果
    should_exit = [False]  # 标记是否应该退出
    history = InMemoryHistory()

    def get_width():
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def get_separator():
        return "─" * get_width()

    while True:
        # 每次循环创建新的 buffer 和 application
        buffer = Buffer(
            history=history,
            multiline=True,
        )

        # 自定义按键绑定
        kb = KeyBindings()

        @kb.add(Keys.ControlJ)
        def _(event):
            event.current_buffer.insert_text("\n")

        @kb.add(Keys.Enter)
        def _(event):
            buf = event.current_buffer
            if buf.text.strip():
                result_text[0] = buf.text
                event.app.exit()

        @kb.add(Keys.ControlC)
        def _(event):
            nonlocal last_ctrl_c_time
            current_time = time.time()
            if current_time - last_ctrl_c_time < 1.0:
                should_exit[0] = True
                event.app.exit()
            else:
                last_ctrl_c_time = current_time
                hint_text[0] = " ^C (再按一次退出)"
                event.current_buffer.reset()
                event.app.invalidate()

        @kb.add(Keys.ControlD)
        def _(event):
            should_exit[0] = True
            event.app.exit()

        def get_height():
            """获取 buffer 的动态高度"""
            text = buffer.text
            if not text:
                return Dimension(min=1, max=10, preferred=1)
            line_count = text.count('\n') + 1
            return Dimension(min=1, max=10, preferred=line_count)

        # 创建布局
        layout = Layout(
            HSplit([
                # 上分隔线
                Window(
                    content=FormattedTextControl(lambda: get_separator()),
                    height=1,
                    style="class:separator",
                ),
                # 输入区域 - 动态高度
                Window(
                    content=BufferControl(buffer=buffer, lexer=SimpleLexer()),
                    height=get_height,
                    wrap_lines=True,
                    left_margins=[],
                    get_line_prefix=lambda line_no, wrap_count: "> " if line_no == 0 and wrap_count == 0 else "  ",
                ),
                # 下分隔线
                Window(
                    content=FormattedTextControl(lambda: get_separator()),
                    height=1,
                    style="class:separator",
                ),
                # 提示信息
                Window(
                    content=FormattedTextControl(lambda: hint_text[0]),
                    height=1,
                    style="class:hint",
                ),
            ])
        )

        # 创建应用
        app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=False,
            mouse_support=False,
        )

        try:
            result_text[0] = None
            app.run()

            if should_exit[0]:
                console.print("\n[dim]会话结束[/dim]")
                break

            if result_text[0]:
                user_input = result_text[0].strip()
                hint_text[0] = " Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"
                if user_input:
                    yield user_input, False
        except EOFError:
            console.print("\n[dim]会话结束[/dim]")
            break


def main():
    args = parse_args()

    llm = ChatOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        model=MODEL,
        temperature=0.7,
        max_tokens=4096,
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
