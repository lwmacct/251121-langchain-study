from pathlib import Path
import sys

from langchain_openai import ChatOpenAI
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from settings import Settings  # noqa: E402


def main():
    print("Hello from app1!")

    try:
        settings = Settings()
    except ValidationError as exc:
        raise RuntimeError(f"配置错误（请检查 OPENROUTER_ 环境变量）：{exc}") from exc

    llm = ChatOpenAI(
        model=settings.model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    response = llm.invoke("给我讲个笑话")
    print()
    print("LLM 响应：")
    print(response.content)


if __name__ == "__main__":
    main()
