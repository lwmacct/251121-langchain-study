from pathlib import Path
import sys

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from settings import Settings  # noqa: E402


def build_llm(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.model,
        base_url=settings.base_url,
        api_key=settings.api_key,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )


def stream_answer(
    llm: ChatOpenAI, messages: list[SystemMessage | HumanMessage | AIMessage]
) -> str:
    """Stream assistant reply and return the accumulated content."""
    chunks: list[str] = []
    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            chunks.append(chunk.content)
    print()
    return "".join(chunks)


def main() -> None:
    print("Hello from app3! 留空回车或 Ctrl+C 退出。")

    try:
        settings = Settings()
    except ValidationError as exc:
        raise RuntimeError(f"配置错误（请检查 OPENROUTER_ 环境变量）：{exc}") from exc

    llm = build_llm(settings)
    history: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content="你是一个简洁、中文回答的助手。"),
    ]

    while True:
        try:
            query = input("\n用户: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n结束对话。")
            break

        if not query:
            print("结束对话。")
            break

        history.append(HumanMessage(content=query))
        print("助手: ", end="", flush=True)
        ai_text = stream_answer(llm, history)
        history.append(AIMessage(content=ai_text))


if __name__ == "__main__":
    main()
