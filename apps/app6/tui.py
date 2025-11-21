"""App6 TUI 模块 - 使用 Textual 实现完整 TUI，避免输出冲突"""

import asyncio
from typing import Callable

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Static, RichLog, TextArea
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
    """聊天 TUI 应用 - 完整控制渲染"""

    CSS = """
    #chat-container {
        height: 1fr;
        border: solid $primary;
    }

    #chat-log {
        height: 1fr;
        scrollbar-gutter: stable;
    }

    #input-container {
        height: auto;
        border: solid $accent;
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
        Binding("ctrl+c", "quit", "退出", show=False),
        Binding("ctrl+d", "quit", "退出", show=False),
    ]

    def __init__(self, on_submit: Callable = None):
        super().__init__()
        self.on_submit = on_submit
        self.pending_count = 0

    def compose(self) -> ComposeResult:
        yield Container(
            RichLog(id="chat-log", wrap=True, highlight=True, markup=True),
            id="chat-container",
        )
        yield Container(
            TextArea(id="input", soft_wrap=True),
            id="input-container",
        )
        yield Static(self._get_status_text(), id="status")

    def on_mount(self) -> None:
        """挂载时聚焦输入框"""
        self.query_one("#input", TextArea).focus()

    def _get_status_text(self) -> str:
        """获取状态栏文本"""
        if self.pending_count > 0:
            return f"⏳ {self.pending_count} 个处理中 | Enter 发送 | Ctrl+J 换行 | Ctrl+C 退出"
        return "Enter 发送 | Ctrl+J 换行 | Ctrl+C 退出"

    def update_status(self) -> None:
        """更新状态栏"""
        status = self.query_one("#status", Static)
        status.update(self._get_status_text())

    async def on_key(self, event: events.Key) -> None:
        """处理按键事件"""
        input_widget = self.query_one("#input", TextArea)

        # 只在输入框聚焦时处理
        if not input_widget.has_focus:
            return

        if event.key == "enter":
            # Enter 发送消息
            text = input_widget.text.strip()
            if text:
                event.prevent_default()
                input_widget.clear()
                self.add_user_message(text)

                # 在后台处理消息
                if self.on_submit:
                    asyncio.create_task(self._process_message(text))

        elif event.key == "ctrl+j":
            # Ctrl+J 换行
            event.prevent_default()
            input_widget.insert("\n")

    async def _process_message(self, text: str) -> None:
        """后台处理消息"""
        try:
            should_exit = await self.on_submit(text)
            if should_exit:
                self.exit()
        except Exception as e:
            self.add_assistant_message(f"错误: {e}", tool_name="Error")

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

    def action_quit(self) -> None:
        """退出应用"""
        self.exit()
