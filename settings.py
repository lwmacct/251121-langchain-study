from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".taskfile/.env",
        env_prefix="OPENROUTER_",
        extra="ignore",  # 忽略运行环境注入的无关变量（如 is_sandbox、uv_link_mode）
    )

    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "anthropic/claude-3.5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4096
