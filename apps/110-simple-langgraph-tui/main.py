#!/usr/bin/env -S uv run python
"""
LangGraph TUI 工具调用演示 - 使用 Rich 库的终端交互界面

演示 LangGraph 工具调用功能，包括时间查询、计算器等工具，并通过 Rich 库提供友好的终端界面
"""


import operator
import os
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich import box

# Import tools from shared workspace library
from m_tools import get_current_time, calculator

# ===== 初始化 =====
console = Console()

# 配置 LLM
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("配置错误:未找到环境变量 OPENROUTER_API_KEY")

llm = ChatOpenAI(
    model="anthropic/claude-sonnet-4.5",
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=api_key,
)

# ===== 配置工具 =====
# 工具列表（从 workspace 库导入）
tool_list = [get_current_time, calculator]

# 创建工具节点
tool_node = ToolNode(tool_list)

# 将工具绑定到模型
llm_with_tools = llm.bind_tools(tool_list)


# ===== 定义状态 =====
class State(TypedDict):
    messages: Annotated[Sequence[AnyMessage], operator.add]


# ===== 定义节点 =====
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


# ===== 构建图 =====
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


# ===== UI 函数 =====
def print_welcome():
    """打印欢迎信息"""
    welcome_text = """# 🤖 TUI 工具调用演示

**可用工具：**
- 🕒 `get_current_time` - 获取当前时间
- 🔢 `calculator` - 执行数学计算

**示例问题：**
- 现在几点了？
- 帮我计算 42 * 7
- 你好，介绍一下你自己
- 你预测人工智能 agi 在哪一年能实现, 那时候 是几几年了, 你来计算一下

输入 `exit` 或 `quit` 退出
"""
    console.print(Panel(Markdown(welcome_text), box=box.ROUNDED, border_style="cyan"))


def print_user_message(message: str):
    """打印用户消息"""
    console.print(f"\n[bold cyan]👤 You:[/bold cyan] {message}")


def print_tool_call(tool_call):
    """打印工具调用信息"""
    tool_name = tool_call.get("name", "unknown")
    tool_args = tool_call.get("args", {})
    console.print(f"[yellow]🔧 调用工具:[/yellow] {tool_name}({tool_args})")


def print_assistant_message(content: str, has_tool_calls: bool = False):
    """打印助手消息"""
    if content:
        console.print(f"[bold green]🤖 Assistant:[/bold green] {content}")
    if not has_tool_calls and not content:
        console.print("[dim]等待工具执行...[/dim]")


# ===== 主循环 =====
def main():
    """主函数"""
    print_welcome()

    # 初始化消息历史
    messages = []

    try:
        while True:
            # 获取用户输入
            user_input = Prompt.ask("\n[bold cyan]💬 You[/bold cyan]")

            # 检查退出命令
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("\n[yellow]👋 再见！[/yellow]")
                break

            # 添加用户消息到历史
            messages.append(HumanMessage(content=user_input))

            # 调用 LangGraph 应用
            console.print("[dim]正在思考...[/dim]")

            # 流式执行图
            for output in app.stream({"messages": messages}):
                # 输出包含节点名称和状态
                for node_name, state in output.items():
                    new_messages = state["messages"]

                    # 处理模型节点的输出
                    if node_name == "model":
                        last_message = new_messages[-1]

                        # 如果有工具调用
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            for tool_call in last_message.tool_calls:
                                print_tool_call(tool_call)

                        # 如果有内容
                        if last_message.content:
                            print_assistant_message(last_message.content)

                    # 处理工具节点的输出
                    elif node_name == "tools":
                        for msg in new_messages:
                            if isinstance(msg, ToolMessage):
                                console.print(f"[green]✅ 工具返回:[/green] {msg.content}")

                    # 更新消息历史
                    messages = state["messages"]

    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 会话已中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ 错误: {e}[/red]")


if __name__ == "__main__":
    main()
