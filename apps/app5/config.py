"""App5 配置模块"""

import os

DEBUG = os.getenv("APP5_DEBUG") == "1"

# OpenRouter 配置
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = "anthropic/claude-3.5-sonnet"

# LLM 参数
TEMPERATURE = 0.7
MAX_TOKENS = 4096
