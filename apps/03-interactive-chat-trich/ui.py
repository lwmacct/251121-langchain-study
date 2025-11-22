"""App6 用户界面模块

优化：提供更简洁的 UI 实现，同时保留 app5 的优秀交互体验
"""

import sys
from typing import Iterator

from rich.console import Console
from rich.text import Text

console = Console()


def print_user(content: str) -> None:
    """打印用户消息

    Args:
        content: 用户输入内容
    """
    console.print(Text("👤 ", style="bold green") + Text(content))


def print_assistant(content: str, tool_calls: list[str] | None = None) -> None:
    """打印助手消息

    Args:
        content: 助手回复内容
        tool_calls: 调用的工具名称列表（可选）
    """
    prefix = Text("🤖 ", style="bold blue")

    if tool_calls:
        tools_text = Text(f"[{', '.join(tool_calls)}] ", style="dim magenta")
        console.print(prefix + tools_text + Text(content))
    else:
        console.print(prefix + Text(content))


def print_system(content: str, style: str = "dim yellow") -> None:
    """打印系统消息

    Args:
        content: 系统消息内容
        style: Rich 样式
    """
    console.print(f"[{style}]ℹ️  {content}[/{style}]")


def print_error(content: str) -> None:
    """打印错误消息

    Args:
        content: 错误内容
    """
    console.print(f"[bold red]❌ {content}[/bold red]")


def get_input_iterator(interactive_after_pipe: bool = False) -> Iterator[tuple[str, bool]]:
    """获取输入迭代器，支持管道和交互式模式

    优化：提供简化的输入处理，专注核心功能

    Args:
        interactive_after_pipe: 管道结束后是否进入交互模式

    Yields:
        (user_input, from_pipe): 用户输入和是否来自管道的标志
    """
    is_piped = not sys.stdin.isatty()

    # 1. 处理管道输入
    if is_piped:
        piped_lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
        for line in piped_lines:
            # 跳过退出命令（管道模式下不需要）
            if line.lower() in ["quit", "exit", "退出", "结束", "q"]:
                continue
            yield line, True  # 来自管道，需要打印

        if not interactive_after_pipe:
            return

        print_system("管道输入处理完毕，进入交互模式（Ctrl+D 或 Ctrl+C 退出）\n")

    # 2. 交互式模式 - 简化版本
    console.print("[dim]───────────────────────────────────────[/dim]")
    console.print("[dim]提示: 输入消息后按 Enter 发送[/dim]")
    console.print("[dim]      Ctrl+C 或输入 'quit' 退出[/dim]")
    console.print("[dim]───────────────────────────────────────[/dim]\n")

    while True:
        try:
            # 使用 Rich 的输入
            user_input = console.input("[bold cyan]>>> [/bold cyan]")

            user_input = user_input.strip()
            if not user_input:
                continue

            # 检查退出命令
            if user_input.lower() in ["quit", "exit", "退出", "结束", "q"]:
                console.print("\n[dim]👋 再见！[/dim]")
                break

            yield user_input, False  # 来自交互，不需要打印

        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]👋 再见！[/dim]")
            break


# 高级 UI 选项：复用 app5 的 prompt_toolkit 实现
try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, BufferControl, Dimension
    from prompt_toolkit.lexers import SimpleLexer
    import time
    import shutil

    ADVANCED_UI_AVAILABLE = True
except ImportError:
    ADVANCED_UI_AVAILABLE = False


def get_advanced_input_iterator(interactive_after_pipe: bool = False) -> Iterator[tuple[str, bool]]:
    """获取输入迭代器 - 高级版本（使用 prompt_toolkit）

    提供多行输入、历史记录、更好的编辑体验

    Args:
        interactive_after_pipe: 管道结束后是否进入交互模式

    Yields:
        (user_input, from_pipe): 用户输入和是否来自管道的标志
    """
    if not ADVANCED_UI_AVAILABLE:
        # 降级到简单版本
        console.print("[yellow]警告: prompt_toolkit 未安装，使用简化输入模式[/yellow]")
        yield from get_input_iterator(interactive_after_pipe)
        return

    is_piped = not sys.stdin.isatty()

    # 1. 处理管道输入
    if is_piped:
        piped_lines = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
        for line in piped_lines:
            # 跳过退出命令（管道模式下不需要）
            if line.lower() in ["quit", "exit", "退出", "结束", "q"]:
                continue
            yield line, True

        if not interactive_after_pipe:
            return

        console.print("\n[dim]─── 进入交互模式 (连按两次 Ctrl+C 退出) ───[/dim]\n")

    # 2. 交互式模式 - 复用 app5 的高级实现
    last_ctrl_c_time = 0
    hint_text = [""]  # 默认为空，避免干扰对话显示
    result_text = [None]
    should_exit = [False]
    history = InMemoryHistory()

    def get_width():
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def get_separator():
        return "─" * get_width()

    while True:
        buffer = Buffer(history=history, multiline=True)
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
                hint_text[0] = "⚠️ 再按一次 Ctrl+C 退出"
                event.current_buffer.reset()
                event.app.invalidate()

                def reset_hint():
                    if hint_text[0] == "⚠️ 再按一次 Ctrl+C 退出":
                        hint_text[0] = ""
                        event.app.invalidate()

                event.app.loop.call_later(1.0, reset_hint)

        @kb.add(Keys.ControlD)
        def _(event):
            should_exit[0] = True
            event.app.exit()

        def get_height():
            text = buffer.text
            line_count = text.count("\n") + 1 if text else 1
            return Dimension(min=1, max=10, preferred=line_count, weight=1)

        layout = Layout(
            HSplit(
                [
                    Window(content=FormattedTextControl(lambda: get_separator()), height=1, style="class:separator"),
                    Window(
                        content=BufferControl(buffer=buffer, lexer=SimpleLexer()),
                        height=get_height,
                        wrap_lines=True,
                        left_margins=[],
                        get_line_prefix=lambda line_no, wrap_count: (f"{line_no + 1}> " if wrap_count == 0 else "   "),
                    ),
                    Window(content=FormattedTextControl(lambda: get_separator()), height=1, style="class:separator"),
                    Window(content=FormattedTextControl(lambda: hint_text[0]), height=1, style="class:hint"),
                ]
            )
        )

        app = Application(layout=layout, key_bindings=kb, full_screen=False, mouse_support=False)

        try:
            result_text[0] = None
            app.run()

            if should_exit[0]:
                console.print("\n[dim]会话结束[/dim]")
                break

            if result_text[0]:
                user_input = result_text[0].strip()
                hint_text[0] = ""
                if user_input:
                    yield user_input, False
        except EOFError:
            console.print("\n[dim]会话结束[/dim]")
            break
