# app.py
import operator
import os
import base64
from typing import Annotated, Sequence, TypedDict

import chainlit as cl
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from utils import compress_image_if_needed
from tools import get_current_time, calculator

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

# ===== 配置工具 =====
# 工具列表
tools = [get_current_time, calculator]

# 创建工具节点
tool_node = ToolNode(tools)

# 将工具绑定到模型
llm_with_tools = llm.bind_tools(tools)


class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], operator.add]


def call_model(state: State) -> State:
    """调用 LLM（带工具）并把回复追加到消息列表"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: State):
    """判断是否需要继续调用工具"""
    messages = state["messages"]
    last_message = messages[-1]
    # 如果最后一条消息有 tool_calls，则路由到工具节点
    if last_message.tool_calls:
        return "tools"
    # 否则结束
    return END


# 构建图
graph = StateGraph(State)

# 添加节点
graph.add_node("model", call_model)
graph.add_node("tools", tool_node)

# 添加边
graph.add_edge(START, "model")
graph.add_conditional_edges(
    "model",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)
graph.add_edge("tools", "model")  # 工具执行后返回模型

# 编译图
app = graph.compile()


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
                compressed_image = compress_image_if_needed(image.path, max_size_mb=5.0, max_dimension=1568, quality=85)  # Claude API 限制 5MB  # Claude 推荐 1568px  # 业界标准
                image_data = base64.b64encode(compressed_image).decode("utf-8")

                # 打印调试信息
                print(f"图片信息: name={image.name}, mime={image.mime}, path={image.path}")
                print(f"Base64 长度: {len(image_data)} (原始文件: {os.path.getsize(image.path)} bytes)")

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

    # 使用流式处理，捕获工具调用过程
    try:
        print("\n" + "=" * 50)
        print("🚀 开始处理用户请求")
        print("=" * 50)

        final_response = None
        tool_call_count = 0

        # 使用 astream 流式处理
        async for event in app.astream({"messages": [human_message]}, stream_mode="values"):
            messages = event.get("messages", [])
            if not messages:
                continue

            last_message = messages[-1]

            # 检测到 AI 消息且有工具调用
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                tool_call_count += 1
                print(f"\n📋 检测到工具调用 (第 {tool_call_count} 轮)")

                # 在界面上显示工具调用信息
                for tool_call in last_message.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})

                    print(f"  🔧 工具: {tool_name}")
                    print(f"  📝 参数: {tool_args}")

                    # 在 Chainlit UI 中显示（使用简单名称避免 avatar URL 问题）
                    async with cl.Step(name=f"Calling {tool_name}", type="tool") as step:
                        step.input = str(tool_args)
                        await step.stream_token(f"🔧 Calling tool: `{tool_name}`\n\n")
                        await step.stream_token(f"📝 Arguments: `{tool_args}`")

            # 检测到工具消息（工具返回结果）
            elif isinstance(last_message, ToolMessage):
                # 这是 ToolMessage
                tool_name = getattr(last_message, "name", "unknown")
                tool_result = last_message.content

                print(f"  ✅ 工具 {tool_name} 返回结果: {tool_result[:100]}...")

                # 在 Chainlit UI 中显示工具结果（使用英文避免编码问题）
                async with cl.Step(name=f"Tool Result: {tool_name}", type="tool") as step:
                    step.output = tool_result

            # 更新最终响应
            final_response = last_message

        print("\n" + "=" * 50)
        print(f"✨ 处理完成 (共调用 {tool_call_count} 轮工具)")
        print("=" * 50 + "\n")

        # 发送最终响应
        if final_response and hasattr(final_response, "content"):
            await cl.Message(content=final_response.content).send()
        else:
            await cl.Message(content="处理完成，但没有收到响应").send()

    except Exception as e:
        # 打印详细错误信息到控制台
        import traceback

        print(f"\n❌ 错误详情：{type(e).__name__}: {e}")
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


"""

uv run chainlit run apps/05-chainlit-tool-call/main.py -whd --host 0.0.0.0 --port 8000

"""
