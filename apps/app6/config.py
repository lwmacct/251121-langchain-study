"""App6 配置模块

优化：使用 dataclass 提供类型安全和更好的配置管理
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """应用配置 - 不可变配置对象"""

    # OpenRouter API 配置
    api_key: str
    base_url: str
    model: str

    # LLM 参数
    temperature: float
    max_tokens: int

    # 调试模式
    debug: bool

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model=os.environ.get("APP6_MODEL", "anthropic/claude-3.5-sonnet"),
            temperature=float(os.environ.get("APP6_TEMPERATURE", "0.7")),
            max_tokens=int(os.environ.get("APP6_MAX_TOKENS", "4096")),
            debug=os.getenv("APP6_DEBUG") == "1",
        )


# 全局配置实例
config = Config.from_env()
