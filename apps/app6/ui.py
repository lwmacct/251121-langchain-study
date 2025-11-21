"""App6 异步用户界面模块 - 底部固定输入区 + 上方滚动输出

设计理念：
- **上方区域**：Rich print 正常输出，终端自然滚动（历史消息）
- **底部固定区域**：prompt_toolkit 输入框，固定占用底部几行
- 后台任务完成时直接 print，输出会向上滚动
- 输入框始终固定在底部可见

界面外观：
  用户: 你好                          ← 终端滚动区域
  助手: [LLM:chat] 你好！...          ← 使用 Rich print
  用户: 现在几点                      ← 正常向上滚动
  助手: [get_current_time] 23:00
  ─────────────────────────────────
  1> 输入内容...                      ← 固定在底部
  ─────────────────────────────────
  ⏳ 2 个处理中 | Ctrl+J 换行 | Enter 发送

关键技术：
- 输出在两次输入之间进行（Application 不运行时）
- 输出完成后重新启动 Application
- 实现"输出向上滚动，输入框固定底部"的效果
"""

import asyncio
import sys
import time
import shutil

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
    """异步聊天界面 - 基于 app5 的 Application 布局 + 异步能力"""

    def __init__(self):
        self.history = InMemoryHistory()
        self.pending_count = 0  # 等待中的 LLM 请求数
        self.should_exit = False
        self.last_ctrl_c_time = 0

    @staticmethod
    def _get_width():
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def _get_separator(self):
        return "─" * self._get_width()

    def _get_hint_text(self):
        """获取提示文本，包含待处理任务数"""
        if self.pending_count > 0:
            return f" ⏳ {self.pending_count} 个处理中 | Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"
        return " Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"

    async def get_input_async(self) -> str | None:
        """异步获取用户输入 - 使用 app5 的 Application 布局"""
        result_text = [None]
        buffer = Buffer(
            history=self.history,
            multiline=True,
        )

        hint_text = [self._get_hint_text()]

        # 按键绑定
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
            current_time = time.time()
            if current_time - self.last_ctrl_c_time < 1.0:
                self.should_exit = True
                event.app.exit()
            else:
                self.last_ctrl_c_time = current_time
                hint_text[0] = " ^C (再按一次退出)"
                event.current_buffer.reset()
                event.app.invalidate()

                def reset_hint():
                    hint_text[0] = self._get_hint_text()
                    if hasattr(event.app, 'invalidate'):
                        event.app.invalidate()

                event.app.loop.call_later(1.0, reset_hint)

        @kb.add(Keys.ControlD)
        def _(event):
            self.should_exit = True
            event.app.exit()

        def get_height():
            """动态高度"""
            text = buffer.text
            line_count = text.count('\n') + 1 if text else 1
            return Dimension(min=1, max=10, preferred=line_count, weight=1)

        # 创建布局（与 app5 相同）
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
                    content=FormattedTextControl(lambda: hint_text[0]),
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
