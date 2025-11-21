"""App6 TUI 模块 - 使用 Textual 实现专业 TUI"""

import asyncio
from typing import Callable

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, RichLog, Footer, TextArea
from textual.binding import Binding
from textual import events

from rich.console import Console
from rich.text import Text

console = Console()


def print_user(content: str):
    """打印用户消息（用于管道模式）"""
    console.print(Text("用户: ", style="bold green") + Text(content))


def print_assistant(content: str, tool_name: str = None):
    """打印助手消息（用于管道模式）"""
    if tool_name:
        tag = Text(f"[{tool_name}] ", style="bold magenta")
        console.print(Text("助手: ", style="bold blue") + tag + Text(content))
    else:
        console.print(Text("助手: ", style="bold blue") + Text(content))


class ChatTUI(App):
    """聊天 TUI 应用"""

    CSS = """
    #chat-container {
        height: 1fr;
        border: solid green;
    }

    #chat-log {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    #input-container {
        height: auto;
        max-height: 10;
        border: solid blue;
    }

    #status {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }

    #input {
        height: auto;
        min-height: 3;
        max-height: 10;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "退出", show=True),
        Binding("ctrl+d", "quit", "退出", show=False),
        Binding("pageup", "scroll_up", "向上滚动", show=False),
        Binding("pagedown", "scroll_down", "向下滚动", show=False),
    ]

    def __init__(self, on_submit: Callable = None):
        super().__init__()
        self.on_submit = on_submit
        self._waiting = False

    def compose(self) -> ComposeResult:
        yield Container(
            RichLog(id="chat-log", wrap=True, highlight=True, markup=True),
            id="chat-container",
        )
        yield Container(
            TextArea(id="input"),
            id="input-container",
        )
        yield Static("Enter 发送 | Ctrl+J 换行 | PageUp/Down 滚动 | Ctrl+C 退出", id="status")

    def on_mount(self) -> None:
        """挂载时聚焦输入框"""
        self.query_one("#input", TextArea).focus()

    def action_scroll_up(self) -> None:
        """向上滚动对话区"""
        log = self.query_one("#chat-log", RichLog)
        log.scroll_up(animate=False)

    def action_scroll_down(self) -> None:
        """向下滚动对话区"""
        log = self.query_one("#chat-log", RichLog)
        log.scroll_down(animate=False)

    async def on_key(self, event: events.Key) -> None:
        """处理按键事件"""
        input_widget = self.query_one("#input", TextArea)

        # 只在输入框聚焦时处理
        if not input_widget.has_focus:
            return

        if event.key == "enter":
            # Enter 发送消息
            if self._waiting:
                event.prevent_default()
                return

            text = input_widget.text.strip()
            if text:
                event.prevent_default()
                await self._submit_message(text)

        elif event.key == "ctrl+j":
            # Ctrl+J 换行
            event.prevent_default()
            input_widget.insert("\n")

    async def _submit_message(self, text: str) -> None:
        """提交消息"""
        # 清空输入框
        input_widget = self.query_one("#input", TextArea)
        input_widget.clear()

        # 添加用户消息
        self.add_user_message(text)

        # 设置等待状态
        self.set_waiting(True)

        # 在后台处理消息
        asyncio.create_task(self._process_message(text))

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        log = self.query_one("#chat-log", RichLog)
        log.write(Text("用户: ", style="bold green") + Text(content))

    def add_assistant_message(self, content: str, tool_name: str = None) -> None:
        """添加助手消息"""
        log = self.query_one("#chat-log", RichLog)
        if tool_name:
            tag = Text(f"[{tool_name}] ", style="bold magenta")
            log.write(Text("助手: ", style="bold blue") + tag + Text(content))
        else:
            log.write(Text("助手: ", style="bold blue") + Text(content))

    def set_waiting(self, waiting: bool) -> None:
        """设置等待状态"""
        self._waiting = waiting
        status = self.query_one("#status", Static)

        if waiting:
            status.update("⏳ 等待响应中... (可编辑，暂不可发送)")
        else:
            status.update("Enter 发送 | Ctrl+J 换行 | PageUp/Down 滚动 | Ctrl+C 退出")

    async def _process_message(self, text: str) -> None:
        """后台处理消息"""
        if self.on_submit:
            try:
                should_exit = await self.on_submit(text)
                if should_exit:
                    self.exit()
            finally:
                self.set_waiting(False)

    def action_quit(self) -> None:
        """退出应用"""
        self.exit()
