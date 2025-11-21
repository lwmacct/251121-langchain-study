"""App6 会话管理模块

优化：将对话历史管理从 main.py 中分离出来，提供清晰的状态管理接口
"""

from dataclasses import dataclass, field
from typing import Iterator

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage


@dataclass
class Session:
    """会话状态管理

    优化点：
    1. 封装历史消息管理逻辑
    2. 提供类型安全的接口
    3. 支持历史限制（避免 token 过多）
    4. 提供便捷的渲染方法
    """

    history: list[BaseMessage] = field(default_factory=list)
    max_history: int = 50  # 最大保留消息数

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.history.append(HumanMessage(content=content))
        self._trim_history()

    def add_assistant_message(self, content: str) -> None:
        """添加助手消息"""
        self.history.append(AIMessage(content=content))
        self._trim_history()

    def get_history(self) -> list[BaseMessage]:
        """获取历史消息（用于传递给 LLM）"""
        return self.history.copy()

    def _trim_history(self) -> None:
        """修剪历史，保持在最大限制内"""
        if len(self.history) > self.max_history:
            # 保留最近的消息
            self.history = self.history[-self.max_history :]

    def render_history(self, limit: int = 10) -> str:
        """渲染历史消息为文本

        Args:
            limit: 最多渲染最近的 N 条消息

        Returns:
            格式化的历史文本
        """
        lines = []
        recent = self.history[-limit:] if limit else self.history

        for msg in recent:
            if isinstance(msg, HumanMessage):
                lines.append(f"👤 用户: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"🤖 助手: {msg.content}")

        return "\n".join(lines) if lines else "(无历史记录)"

    def get_message_count(self) -> int:
        """获取消息总数"""
        return len(self.history)

    def clear(self) -> None:
        """清空历史"""
        self.history.clear()

    def iter_pairs(self) -> Iterator[tuple[HumanMessage, AIMessage | None]]:
        """迭代消息对（用户消息 + 对应的助手回复）

        Yields:
            (用户消息, 助手消息 或 None)
        """
        i = 0
        while i < len(self.history):
            if isinstance(self.history[i], HumanMessage):
                user_msg = self.history[i]
                assistant_msg = None

                # 查找下一条助手消息
                if i + 1 < len(self.history) and isinstance(
                    self.history[i + 1], AIMessage
                ):
                    assistant_msg = self.history[i + 1]
                    i += 2
                else:
                    i += 1

                yield user_msg, assistant_msg
            else:
                i += 1
