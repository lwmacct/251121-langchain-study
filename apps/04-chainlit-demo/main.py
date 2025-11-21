# app.py
import operator
import os
from typing import Annotated, Sequence, TypedDict

import chainlit as cl
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

# 或者 from langchain_volcengine import ChatVolcEngine 等

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("配置错误:未找到环境变量 OPENROUTER_API_KEY")

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4.5",
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=api_key,
    streaming=True,
)  # 换成你的模型


class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], operator.add]


def call_model(state: State) -> State:
    """简单的对话节点，调用 LLM 并把回复追加到消息列表"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


graph = StateGraph(State)
graph.add_node("model", call_model)
graph.add_edge(START, "model")
graph.add_edge("model", END)
app = graph.compile()


@cl.on_chat_start
async def start():
    await cl.Message(content="我准备好了！问我任何事～").send()


@cl.on_message
async def main(message: cl.Message):
    # 支持文件上传、图片等
    if message.elements:
        # 处理上传文件...
        pass

    # 直接跑你的 LangGraph
    try:
        response = await app.ainvoke({"messages": [HumanMessage(content=message.content)]})
    except Exception as e:
        await cl.Message(content=f"LLM 调用失败：{e}").send()
        return

    await cl.Message(content=response["messages"][-1].content).send()


"""

uv run chainlit run apps/04-chainlit-demo/main.py -whd --host 0.0.0.0 --port 8000 


"""
