"""
Streamlit + LangGraph 工具调用演示
====================================
展示如何在 Streamlit 中集成 LangGraph 和工具调用功能
"""

import os
import operator
from typing import Annotated, Sequence, TypedDict

import streamlit as st
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# 导入工具
from m_tools import get_current_time, calculator

# ===== 配置 API =====
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("配置错误:未找到环境变量 OPENROUTER_API_KEY")

# 创建 LLM 实例
llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4.5",
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=api_key,
    temperature=0.7,
    streaming=True,
)

# ===== 配置工具 =====
tools = [get_current_time, calculator]
tool_node = ToolNode(tools)
llm_with_tools = llm.bind_tools(tools)


# ===== LangGraph 状态定义 =====
class State(TypedDict):
    """LangGraph 状态"""

    messages: Annotated[Sequence[AnyMessage], operator.add]


def call_model(state: State) -> State:
    """调用 LLM（带工具）"""
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: State):
    """判断是否需要继续调用工具"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END


# ===== 构建 LangGraph =====
graph = StateGraph(State)
graph.add_node("model", call_model)
graph.add_node("tools", tool_node)
graph.add_edge(START, "model")
graph.add_conditional_edges("model", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "model")
app = graph.compile()


# ===== Streamlit UI =====
st.set_page_config(page_title="LangGraph + Streamlit 工具调用演示", page_icon="🤖", layout="wide")

st.title("🤖 LangGraph + Streamlit 工具调用演示")

# 侧边栏：说明和预设问题
with st.sidebar:
    st.header("✨ 功能说明")
    st.markdown(
        """
    这是一个智能 AI 助手，具备以下能力：

    **🔧 可用工具**
    - `get_current_time` - 获取当前时间
    - `calculator` - 执行数学计算

    **👁️ 可视化**
    - 实时显示工具调用过程
    - 展示工具参数和返回结果
    """
    )

    st.divider()
    st.header("🎬 预设问题")

    # 预设问题按钮
    if st.button("⏰ 查询当前时间", use_container_width=True):
        st.session_state["preset_question"] = "现在几点了？请告诉我当前的时间。"

    if st.button("🔢 数学计算", use_container_width=True):
        st.session_state["preset_question"] = "请帮我计算 42 * 7 等于多少？"

    if st.button("🔧 多工具组合", use_container_width=True):
        st.session_state["preset_question"] = "现在几点了？另外帮我算一下 100 除以 4 等于多少。"

    if st.button("🤖 AGI 预测", use_container_width=True):
        st.session_state["preset_question"] = "你觉得人工智能 AGI 在多少年后实现，那时是几几年？"

    if st.button("💬 普通对话", use_container_width=True):
        st.session_state["preset_question"] = "你好！请介绍一下你自己和你的能力。"

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理预设问题
if "preset_question" in st.session_state:
    prompt = st.session_state.preset_question
    del st.session_state.preset_question
else:
    prompt = st.chat_input("说点什么吧...")

# 处理用户输入
if prompt:
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 LangGraph 处理
    with st.chat_message("assistant"):
        # 创建占位符用于显示过程
        status_placeholder = st.empty()
        tool_info_placeholder = st.container()
        response_placeholder = st.empty()

        # 构建消息
        human_message = HumanMessage(content=prompt)

        # 收集所有状态
        final_response = None
        tool_calls_info = []

        try:
            # 使用状态栏显示处理状态
            with status_placeholder.status("🤔 思考中...", expanded=True) as status:
                # 流式处理
                for event in app.stream({"messages": [human_message]}, stream_mode="values"):
                    messages = event.get("messages", [])
                    if not messages:
                        continue

                    last_message = messages[-1]

                    # 检测 AI 消息且有工具调用
                    if isinstance(last_message, AIMessage) and last_message.tool_calls:
                        status.update(label="🔧 调用工具中...", state="running")

                        for tool_call in last_message.tool_calls:
                            tool_name = tool_call.get("name", "unknown")
                            tool_args = tool_call.get("args", {})

                            tool_calls_info.append(
                                {
                                    "type": "call",
                                    "name": tool_name,
                                    "args": tool_args,
                                }
                            )

                    # 检测工具消息（工具返回结果）
                    elif isinstance(last_message, ToolMessage):
                        tool_name = getattr(last_message, "name", "unknown")
                        tool_result = last_message.content

                        tool_calls_info.append(
                            {
                                "type": "result",
                                "name": tool_name,
                                "result": tool_result,
                            }
                        )

                    # 更新最终响应
                    final_response = last_message

                status.update(label="✅ 处理完成", state="complete")

            # 显示工具调用信息
            if tool_calls_info:
                with tool_info_placeholder.expander("🔧 工具调用详情", expanded=True):
                    for i, info in enumerate(tool_calls_info):
                        if info["type"] == "call":
                            st.markdown(f"**🔧 调用工具:** `{info['name']}`")
                            st.code(f"参数: {info['args']}", language="python")
                        elif info["type"] == "result":
                            st.markdown(f"**✅ 工具结果:** `{info['name']}`")
                            st.success(info["result"])

                        if i < len(tool_calls_info) - 1:
                            st.divider()

            # 显示最终响应
            if final_response and hasattr(final_response, "content"):
                response_content = final_response.content
                response_placeholder.markdown(response_content)
                st.session_state.messages.append({"role": "assistant", "content": response_content})
            else:
                error_msg = "处理完成，但没有收到响应"
                response_placeholder.warning(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

        except Exception as e:
            status_placeholder.empty()
            error_msg = f"❌ 错误: {type(e).__name__}: {str(e)}"
            response_placeholder.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})


# ===== 页脚信息 =====
st.divider()
st.caption("💡 提示: 尝试问我时间、让我做数学计算，或者直接聊天！")
