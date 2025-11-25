#!/usr/bin/env -S uv run python
"""
LangChain 基础调用演示 - 使用 invoke 方法进行 LLM 对话

演示 LangChain 最基本的 LLM 调用方式（同步、非流式）
"""
import os

from langchain_openai import ChatOpenAI


def main():
    print("Hello from one-simple-chat-invoke!")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("配置错误:未找到环境变量 OPENROUTER_API_KEY")

    llm = ChatOpenAI(model="anthropic/claude-sonnet-4.5", base_url="https://openrouter.ai/api/v1", api_key=api_key)

    response = llm.invoke("请用三句话介绍一下 LangChain")
    print()
    print("LLM 响应:")
    print(response.content)


if __name__ == "__main__":
    main()
