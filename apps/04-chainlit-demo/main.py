# app.py
import operator
import os
import base64
import io
from typing import Annotated, Sequence, TypedDict
from PIL import Image


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


def compress_image(image_path: str, max_size: int = 1024, quality: int = 85) -> bytes:
    """
    压缩图片以减小文件大小

    Args:
        image_path: 图片文件路径
        max_size: 最大宽度或高度（像素）
        quality: JPEG 质量（1-100）

    Returns:
        压缩后的图片字节数据
    """
    # 打开图片
    img = Image.open(image_path)

    # 转换 RGBA 为 RGB（如果需要）
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background

    # 计算新尺寸（保持宽高比）
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # 保存到字节流
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()


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
            # 压缩图片并转换为 base64
            try:
                compressed_image = compress_image(image.path, max_size=1024, quality=85)
                image_data = base64.b64encode(compressed_image).decode("utf-8")

                # 打印调试信息
                print(f"图片信息: name={image.name}, mime={image.mime}, path={image.path}")
                print(f"压缩后 Base64 长度: {len(image_data)} (原始: {os.path.getsize(image.path)})")

                # 添加图片内容块（统一使用 JPEG MIME 类型）
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}})
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


"""

uv run chainlit run apps/04-chainlit-demo/main.py -whd --host 0.0.0.0 --port 8000 


"""
