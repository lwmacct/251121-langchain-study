"""
Chainlit 消息处理器
==================
包含所有用户消息处理的核心业务逻辑，与 LangGraph agent 集成。
"""

import os
import base64
from typing import Optional, List

import chainlit as cl
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

import utils


async def handle_user_message(app, content_text: str, image_elements: Optional[List] = None):  # LangGraph 编译的应用
    """
    处理用户消息的核心业务逻辑

    这个函数协调了整个消息处理流程：
    1. 构建多模态消息内容（文本 + 图片）
    2. 通过 LangGraph agent 处理消息
    3. 捕获并显示工具调用过程
    4. 流式返回最终响应

    Args:
        app: LangGraph 编译的应用实例（包含 agent 工作流）
        content_text: 用户输入的文本内容
        image_elements: 可选的图片元素列表（来自 cl.Message.elements）

    Returns:
        None（通过 Chainlit 发送消息到 UI）
    """
    # ===== 1. 构建多模态消息内容 =====
    content = []

    # 添加文本内容
    if content_text:
        content.append({"type": "text", "text": content_text})

    # 处理上传的图片
    if image_elements:
        images = [file for file in image_elements if file.mime and "image" in file.mime]

        for image in images:
            # 智能压缩图片（仅在必要时）并转换为 base64
            try:
                compressed_image = utils.compress_image_if_needed(
                    image.path, max_size_mb=5.0, max_dimension=1568, quality=85
                )  # Claude API 限制 5MB  # Claude 推荐 1568px  # 业界标准
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

    # ===== 2. 构建 LangChain 消息对象 =====
    human_message = HumanMessage(content=content)

    # 打印消息结构（截断 base64 以避免过长）
    print(f"发送的消息内容块数量: {len(content)}")
    for i, block in enumerate(content):
        if block.get("type") == "text":
            print(f"  块 {i}: 文本 = {block['text'][:50]}...")
        elif block.get("type") == "image_url":
            url = block["image_url"]["url"]
            print(f"  块 {i}: 图片 URL 前缀 = {url[:100]}...")

    # ===== 3. 通过 LangGraph 处理消息 =====
    try:
        print("\n" + "=" * 50)
        print("🚀 开始处理用户请求")
        print("=" * 50)

        final_response = None
        tool_call_count = 0

        # 使用 astream 流式处理（监控每个状态变化）
        async for event in app.astream({"messages": [human_message]}, stream_mode="values"):
            messages = event.get("messages", [])
            if not messages:
                continue

            last_message = messages[-1]

            # ===== 3.1 检测到 AI 消息且有工具调用 =====
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

            # ===== 3.2 检测到工具消息（工具返回结果）=====
            elif isinstance(last_message, ToolMessage):
                tool_name = getattr(last_message, "name", "unknown")
                tool_result = last_message.content

                print(f"  ✅ 工具 {tool_name} 返回结果: {tool_result[:100]}...")

                # 在 Chainlit UI 中显示工具结果
                async with cl.Step(name=f"Tool Result: {tool_name}", type="tool") as step:
                    step.output = tool_result

            # 更新最终响应
            final_response = last_message

        print("\n" + "=" * 50)
        print(f"✨ 处理完成 (共调用 {tool_call_count} 轮工具)")
        print("=" * 50 + "\n")

        # ===== 4. 发送最终响应 =====
        if final_response and hasattr(final_response, "content"):
            await cl.Message(content=final_response.content).send()
        else:
            await cl.Message(content="处理完成，但没有收到响应").send()

    except Exception as e:
        # ===== 错误处理 =====
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
