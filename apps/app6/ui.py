"""App6 异步用户界面模块 - 支持并发输入编辑"""

import asyncio
import sys
import time
import shutil
from typing import Callable, Any

from rich.console import Console
from rich.text import Text
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, BufferControl, Dimension
from prompt_toolkit.lexers import SimpleLexer

console = Console()


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


class AsyncChatUI:
    """异步聊天界面 - 支持在等待 LLM 时继续编辑输入"""

    def __init__(self):
        self.history = InMemoryHistory()
        self.pending_count = 0  # 等待中的 LLM 请求数
        self.hint_text = "Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"
        self.last_ctrl_c_time = 0
        self.should_exit = False
        self._current_app = None
        self._waiting_response = False  # 是否正在等待响应

    def _get_width(self):
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def _get_separator(self):
        return "─" * self._get_width()

    def _get_status_hint(self):
        """获取状态提示，包含等待状态"""
        if self._waiting_response:
            return f" [yellow]⏳ 等待响应中... (可编辑，暂不可发送)[/yellow]"
        return f" {self.hint_text}"

    def set_waiting(self, waiting: bool):
        """设置等待状态"""
        self._waiting_response = waiting
        if self._current_app:
            self._current_app.invalidate()

    def update_pending(self, delta: int):
        """更新等待中的请求数"""
        self.pending_count = max(0, self.pending_count + delta)
        if self._current_app:
            self._current_app.invalidate()

    async def get_input_async(self) -> str | None:
        """异步获取用户输入"""
        result_text = [None]

        buffer = Buffer(
            history=self.history,
            multiline=True,
        )

        kb = KeyBindings()

        @kb.add(Keys.ControlJ)
        def _(event):
            event.current_buffer.insert_text("\n")

        @kb.add(Keys.Enter)
        def _(event):
            # 等待响应期间不允许发送
            if self._waiting_response:
                return
            buf = event.current_buffer
            if buf.text.strip():
                result_text[0] = buf.text
                event.app.exit()

        @kb.add(Keys.ControlC)
        def _(event):
            current_time = time.time()
            if current_time - self.last_ctrl_c_time < 1.0:
                self.should_exit = True
                event.app.exit()
            else:
                self.last_ctrl_c_time = current_time
                self.hint_text = "^C (再按一次退出)"
                event.current_buffer.reset()
                event.app.invalidate()

                def reset_hint():
                    if self.hint_text == "^C (再按一次退出)":
                        self.hint_text = "Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"
                        if self._current_app:
                            self._current_app.invalidate()

                event.app.loop.call_later(1.0, reset_hint)

        @kb.add(Keys.ControlD)
        def _(event):
            self.should_exit = True
            event.app.exit()

        def get_height():
            text = buffer.text
            line_count = text.count('\n') + 1 if text else 1
            return Dimension(min=1, max=10, preferred=line_count, weight=1)

        layout = Layout(
            HSplit([
                Window(
                    content=FormattedTextControl(lambda: self._get_separator()),
                    height=1,
                    style="class:separator",
                ),
                Window(
                    content=BufferControl(buffer=buffer, lexer=SimpleLexer()),
                    height=get_height,
                    wrap_lines=True,
                    left_margins=[],
                    get_line_prefix=lambda line_no, wrap_count: f"{line_no + 1}> " if wrap_count == 0 else "   ",
                ),
                Window(
                    content=FormattedTextControl(lambda: self._get_separator()),
                    height=1,
                    style="class:separator",
                ),
                Window(
                    content=FormattedTextControl(lambda: self._get_status_hint()),
                    height=1,
                    style="class:hint",
                ),
            ])
        )

        app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=False,
            mouse_support=False,
        )

        self._current_app = app

        try:
            await app.run_async()
            if self.should_exit:
                return None
            if result_text[0]:
                return result_text[0].strip()
            return None
        except EOFError:
            self.should_exit = True
            return None
        finally:
            self._current_app = None


async def get_input_iterator_async(interactive_after_pipe: bool = False):
    """异步获取输入迭代器"""
    is_piped = not sys.stdin.isatty()

    if is_piped:
        piped_lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
        for line in piped_lines:
            yield line, True

        if not interactive_after_pipe:
            return

        console.print("\n[dim]─── 进入交互模式 (连按两次 Ctrl+C 退出) ───[/dim]\n")

    ui = AsyncChatUI()

    while not ui.should_exit:
        user_input = await ui.get_input_async()
        if user_input is None:
            if ui.should_exit:
                console.print("\n[dim]会话结束[/dim]")
            break
        yield user_input, False


# 同步版本保留兼容性
def get_input_iterator(interactive_after_pipe: bool = False):
    """同步版本获取输入"""
    async def _wrapper():
        results = []
        async for item in get_input_iterator_async(interactive_after_pipe):
            results.append(item)
        return results

    for item in asyncio.get_event_loop().run_until_complete(_wrapper()):
        yield item
