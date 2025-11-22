# app.py
import operator
import os
import base64
from typing import Annotated, Sequence, TypedDict

import chainlit as cl
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from m_utils import compress_image_if_needed

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
    # 构建消息内容（支持多模态）
    content = []

    # 添加文本内容
    if message.content:
        content.append({"type": "text", "text": message.content})

    # 处理上传的图片
    if message.elements:
        images = [file for file in message.elements if file.mime and "image" in file.mime]

        for image in images:
            # 智能压缩图片（仅在必要时）并转换为 base64
            try:
                compressed_image = compress_image_if_needed(
                    image.path, max_size_mb=5.0, max_dimension=1568, quality=85
                )  # Claude API 限制 5MB  # Claude 推荐 1568px  # 业界标准
                image_data = base64.b64encode(compressed_image).decode("utf-8")

                # 打印调试信息
                print(f"图片信息: name={image.name}, mime={image.mime}, path={image.path}")
                print(f"Base64 长度: {len(image_data)} (原始文件: {os.path.getsize(image.path)} bytes)")

                # 添加图片内容块（统一使用 JPEG MIME 类型）
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    }
                )

            except Exception as e:
                print(f"图片处理失败: {e}")
                await cl.Message(content=f"图片处理失败: {e}").send()
                return

        if images:
            await cl.Message(content=f"收到 {len(images)} 张图片，正在分析...").send()

    # 如果没有任何内容，返回提示
    if not content:
        await cl.Message(content="请发送文本或图片").send()
        return

    # 构建 HumanMessage（多模态）
    human_message = HumanMessage(content=content)

    # 打印消息结构（截断 base64 以避免过长）
    print(f"发送的消息内容块数量: {len(content)}")
    for i, block in enumerate(content):
        if block.get("type") == "text":
            print(f"  块 {i}: 文本 = {block['text'][:50]}...")
        elif block.get("type") == "image_url":
            url = block["image_url"]["url"]
            print(f"  块 {i}: 图片 URL 前缀 = {url[:100]}...")

    # 直接跑你的 LangGraph
    try:
        response = await app.ainvoke({"messages": [human_message]})
    except Exception as e:
        # 打印详细错误信息到控制台
        import traceback

        print(f"错误详情：{type(e).__name__}: {e}")
        print(f"完整堆栈：\n{traceback.format_exc()}")

        # 尝试提取更多错误信息
        error_msg = f"LLM 调用失败：{type(e).__name__}: {str(e)}"
        if hasattr(e, "response"):
            print(f"API 响应: {e.response}")
            error_msg += f"\nAPI 响应: {e.response}"
        if hasattr(e, "body"):
            print(f"错误体: {e.body}")
            error_msg += f"\n错误体: {e.body}"

        await cl.Message(content=error_msg).send()
        return

    await cl.Message(content=response["messages"][-1].content).send()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 启动命令:")
    print(f"  uv run chainlit run {__file__} -whd --host 0.0.0.0 --port 8000")
    print("\n访问地址: http://localhost:8000")
    print("=" * 60 + "\n")
