"""App6 专业 TUI 模块 - 分离对话区和输入区"""

import asyncio
import time
import shutil
from typing import Callable

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, HSplit, Window, FormattedTextControl, BufferControl, Dimension
from prompt_toolkit.layout.containers import ConditionalContainer
from prompt_toolkit.lexers import SimpleLexer


class ChatTUI:
    """专业聊天 TUI - 分离对话区和输入区"""

    def __init__(self, on_submit: Callable[[str], None] = None):
        """
        Args:
            on_submit: 用户提交消息时的回调函数
        """
        self.on_submit = on_submit
        self.history = InMemoryHistory()
        self.chat_content = []  # 存储对话内容
        self.hint_text = "Ctrl+J 换行 | Enter 发送 | Ctrl+C 退出"
        self.last_ctrl_c_time = 0
        self.should_exit = False
        self._waiting_response = False
        self._app = None

        # 创建缓冲区
        self._input_buffer = Buffer(
            history=self.history,
            multiline=True,
            on_text_changed=lambda _: self._on_input_changed(),
        )

        self._chat_buffer = Buffer(
            read_only=True,
            document=Document(""),
        )

    def _get_width(self):
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    def _get_separator(self):
        return "─" * self._get_width()

    def _get_status_hint(self):
        """获取状态提示"""
        if self._waiting_response:
            return " ⏳ 等待响应中... (可编辑，暂不可发送)"
        return f" {self.hint_text}"

    def _on_input_changed(self):
        """输入内容变化时刷新"""
        if self._app:
            self._app.invalidate()

    def _get_input_height(self):
        """动态计算输入框高度"""
        text = self._input_buffer.text
        line_count = text.count('\n') + 1 if text else 1
        return Dimension(min=1, max=10, preferred=line_count, weight=1)

    def set_waiting(self, waiting: bool):
        """设置等待状态"""
        self._waiting_response = waiting
        if self._app:
            self._app.invalidate()

    def add_message(self, role: str, content: str, tag: str = None):
        """添加消息到对话区"""
        if tag:
            line = f"{role}: [{tag}] {content}"
        else:
            line = f"{role}: {content}"
        self.chat_content.append(line)

        # 更新对话区缓冲区
        full_text = "\n".join(self.chat_content)
        self._chat_buffer.set_document(
            Document(full_text, cursor_position=len(full_text)),
            bypass_readonly=True
        )

        if self._app:
            self._app.invalidate()

    def add_user_message(self, content: str):
        """添加用户消息"""
        self.add_message("用户", content)

    def add_assistant_message(self, content: str, tool_name: str = None):
        """添加助手消息"""
        self.add_message("助手", content, tool_name)

    def _create_layout(self):
        """创建 TUI 布局"""
        # 按键绑定
        kb = KeyBindings()

        @kb.add(Keys.ControlJ)
        def _(event):
            event.current_buffer.insert_text("\n")

        @kb.add(Keys.Enter)
        def _(event):
            if self._waiting_response:
                return
            text = self._input_buffer.text.strip()
            if text:
                # 清空输入框
                self._input_buffer.reset()
                # 触发提交回调
                if self.on_submit:
                    asyncio.create_task(self._handle_submit(text))

        @kb.add(Keys.ControlC)
        def _(event):
            current_time = time.time()
            if current_time - self.last_ctrl_c_time < 1.0:
                self.should_exit = True
                event.app.exit()
            else:
                self.last_ctrl_c_time = current_time
                self.hint_text = "^C (再按一次退出)"
                self._input_buffer.reset()
                event.app.invalidate()

                def reset_hint():
                    if self.hint_text == "^C (再按一次退出)":
                        self.hint_text = "Ctrl+J 换行 | Enter 发送 | Ctrl+C 退出"
                        if self._app:
                            self._app.invalidate()

                event.app.loop.call_later(1.0, reset_hint)

        @kb.add(Keys.ControlD)
        def _(event):
            self.should_exit = True
            event.app.exit()

        # 输入区域控件
        input_window = Window(
            content=BufferControl(buffer=self._input_buffer, lexer=SimpleLexer()),
            height=self._get_input_height,
            wrap_lines=True,
            get_line_prefix=lambda line_no, wrap_count: f"{line_no + 1}> " if wrap_count == 0 else "   ",
        )

        # 布局
        root_container = HSplit([
            # 对话内容区 - 占据大部分空间
            Window(
                content=BufferControl(buffer=self._chat_buffer),
                wrap_lines=True,
                height=Dimension(weight=1),  # 自动填充剩余空间
            ),
            # 分隔线
            Window(
                content=FormattedTextControl(lambda: self._get_separator()),
                height=1,
            ),
            # 输入区域
            input_window,
            # 分隔线
            Window(
                content=FormattedTextControl(lambda: self._get_separator()),
                height=1,
            ),
            # 状态提示
            Window(
                content=FormattedTextControl(lambda: self._get_status_hint()),
                height=1,
            ),
        ])

        # 设置焦点到输入窗口
        layout = Layout(root_container, focused_element=input_window)

        return layout, kb

    async def _handle_submit(self, text: str):
        """处理提交"""
        if self.on_submit:
            await self.on_submit(text)

    async def run(self):
        """运行 TUI"""
        layout, kb = self._create_layout()

        self._app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=False,
        )

        try:
            await self._app.run_async()
        finally:
            self._app = None

    def exit(self):
        """退出应用"""
        self.should_exit = True
        if self._app:
            self._app.exit()
