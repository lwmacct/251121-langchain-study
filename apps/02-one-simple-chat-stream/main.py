import os

from langchain_openai import ChatOpenAI


def stream_chat(llm: ChatOpenAI, prompt: str) -> None:
    print("LLM 流式输出:", flush=True)
    for chunk in llm.stream(prompt):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print()


def main():
    print("Hello from one-simple-chat-stream!")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("配置错误:未找到环境变量 OPENROUTER_API_KEY")

    llm = ChatOpenAI(
        model="anthropic/claude-sonnet-4.5",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    stream_chat(llm, "请用三句话介绍一下 LangChain,并分行流式输出")


if __name__ == "__main__":
    main()
