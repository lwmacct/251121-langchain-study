"""App5 用户界面模块 - 输入/输出处理"""

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

                # 1秒后恢复默认提示
                def reset_hint():
                    if hint_text[0] == " ^C (再按一次退出)":
                        hint_text[0] = " Ctrl+J 换行 | Enter 发送 | 连按两次 Ctrl+C 退出"
                        event.app.invalidate()

                event.app.loop.call_later(1.0, reset_hint)

        @kb.add(Keys.ControlD)
        def _(event):
            should_exit[0] = True
            event.app.exit()

        def get_height():
            """获取 buffer 的动态高度 - 基于实际换行符数量"""
            text = buffer.text
            # 只计算用户手动添加的换行符，默认单行
            line_count = text.count('\n') + 1 if text else 1
            return Dimension(min=1, max=10, preferred=line_count, weight=1)

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
                    get_line_prefix=lambda line_no, wrap_count: f"{line_no + 1}> " if wrap_count == 0 else "   ",
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
