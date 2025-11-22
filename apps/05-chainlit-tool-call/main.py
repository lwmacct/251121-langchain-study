# app.py
import operator
import os
from typing import Annotated, Sequence, TypedDict

import chainlit as cl
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI


# app 组件导入
import handlers


# Import tools from shared workspace library
from m_tools import get_current_time, calculator

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
# 工具列表（从 workspace 库导入）
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
graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "model")  # 工具执行后返回模型

# 编译图
app = graph.compile()


# ===== 预设问题配置 =====
PRESET_QUESTIONS = [
    {
        "name": "time_query",
        "label": "⏰ 查询当前时间",
        "question": "现在几点了？请告诉我当前的时间。",
        "description": "触发 get_current_time 工具",
    },
    {
        "name": "math_calc",
        "label": "🔢 数学计算",
        "question": "请帮我计算 42 * 7 等于多少？",
        "description": "触发 calculator 工具",
    },
    {
        "name": "multi_tool",
        "label": "🔧 多工具组合",
        "question": "现在几点了？另外帮我算一下 100 除以 4 等于多少。",
        "description": "同时触发多个工具",
    },
    {
        "name": "agi_question",
        "label": "🤖 AGI 预测",
        "question": "你觉得人工智能 AGI 在多少年后实现，那时是几几年？",
        "description": "时间查询 + 推理",
    },
    {
        "name": "normal_chat",
        "label": "💬 普通对话",
        "question": "你好！请介绍一下你自己和你的能力。",
        "description": "不触发工具",
    },
]


@cl.on_chat_start
async def on_chat_start():
    """
    聊天开始时的钩子：显示欢迎消息和预设问题供用户选择
    """
    # 发送欢迎消息
    await cl.Message(
        content="""# 🎯 欢迎使用 LangGraph + Chainlit 工具调用演示！

这是一个智能 AI 助手，具备以下能力：

✨ **核心功能**
- 🔧 **工具调用**: 可以调用时间查询、计算器等工具
- 🖼️ **多模态支持**: 支持文本和图片分析
- 👁️ **可视化追踪**: 实时显示工具执行过程

📋 **可用工具**
1. `get_current_time` - 获取当前时间
2. `calculator` - 执行数学计算

---

请从下方选择一个预设问题开始体验，或直接输入你的问题：
"""
    ).send()

    # 构建 Action 列表
    actions = [
        cl.Action(name=q["name"], payload={"question": q["question"]}, label=q["label"], description=q["description"])
        for q in PRESET_QUESTIONS
    ]

    # 询问用户选择
    res = await cl.AskActionMessage(
        content="**🎬 选择一个预设问题开始：**", actions=actions, timeout=300, raise_on_timeout=False
    ).send()  # 5 分钟超时

    # 处理用户选择
    if res and res.get("payload"):
        selected_question = res["payload"]["question"]

        # 显示用户选择的问题
        await cl.Message(content=f"**你选择的问题：** {selected_question}", author="User").send()

        # 处理选中的问题（传入 app 对象）
        await handlers.handle_user_message(app, selected_question)
    else:
        # 用户未选择或超时
        await cl.Message(content="💡 **提示**: 你可以直接输入问题开始对话，或上传图片进行分析！").send()


@cl.on_message
async def main(message: cl.Message):
    """
    处理用户发送的消息（支持文本和图片）
    """
    # 调用 handler 处理消息（传入 app 对象）
    await handlers.handle_user_message(app, message.content, message.elements)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 启动命令:")
    print(f"  uv run chainlit run {__file__} -w")
    print("\n访问地址: http://localhost:8000")
    print("=" * 60 + "\n")
