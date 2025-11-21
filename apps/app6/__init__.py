"""App6: 优化的聊天应用

基于 LangChain bind_tools 的智能工具调用系统
"""

from .agent import Agent, create_agent
from .config import Config, config
from .session import Session

__all__ = ["Agent", "create_agent", "Config", "config", "Session"]
