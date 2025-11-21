"""App6 Agent 模块

核心优化：使用 LangChain 的 bind_tools 让 LLM 自动决定何时调用工具
消除 app5 中的手动意图路由逻辑
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from rich.console import Console

from .config import config

console = Console()


class Agent:
    """智能代理 - 封装 LLM 和工具调用逻辑

    优化点：
    1. 使用 bind_tools() 让 LLM 自动判断何时调用工具
    2. 统一处理工具调用和普通对话
    3. 自动处理工具调用循环（tool -> response -> tool...）
    """

    def __init__(self, tools: list[BaseTool]):
        """初始化 Agent

        Args:
            tools: 可用工具列表
        """
        # 创建基础 LLM
        self.llm = ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        # 绑定工具 - LLM 现在知道可以调用这些工具
        self.llm_with_tools = self.llm.bind_tools(tools)

        # 工具映射：name -> tool object
        self.tools_map = {tool.name: tool for tool in tools}

        # 系统提示
        self.system_prompt = """你是一个有帮助的中文助手。

你可以使用工具来获取实时信息或执行操作。当用户的问题需要工具帮助时，请调用相应的工具。

注意：
- 当用户问"现在几点"时，使用 get_current_time 工具
- 当用户需要数学计算时，使用 calculate 工具
- 对于一般对话或基于已知信息的推理，直接回答即可
- 保持回答简洁、友好"""

    def chat(self, user_input: str, history: list) -> tuple[str, list[str] | None]:
        """处理用户输入并返回回复

        Args:
            user_input: 用户输入文本
            history: 对话历史（不包含当前输入）

        Returns:
            (reply, tool_calls): 回复文本和调用的工具名称列表
        """
        # 构建消息列表
        messages = [SystemMessage(content=self.system_prompt)]
        messages.extend(history)
        messages.append(HumanMessage(content=user_input))

        tool_calls_made = []

        # 工具调用循环：LLM 可能需要多次调用工具
        max_iterations = 5
        for iteration in range(max_iterations):
            try:
                response = self.llm_with_tools.invoke(messages)

                # 检查是否需要调用工具
                if not response.tool_calls:
                    # 没有工具调用，直接返回 LLM 的回复
                    return response.content, tool_calls_made if tool_calls_made else None

                # 处理工具调用
                messages.append(response)  # 添加 LLM 的工具调用消息

                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    if config.debug:
                        console.print(
                            f"[dim cyan]→ 工具调用: {tool_name}({tool_args})[/dim cyan]"
                        )

                    # 执行工具
                    if tool_name in self.tools_map:
                        try:
                            tool = self.tools_map[tool_name]
                            result = tool.invoke(tool_args)
                            tool_calls_made.append(tool_name)

                            if config.debug:
                                console.print(f"[dim cyan]← 工具结果: {result}[/dim cyan]")

                            # 添加工具执行结果
                            messages.append(
                                ToolMessage(
                                    content=str(result),
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                )
                            )
                        except Exception as e:
                            error_msg = f"工具执行错误：{e}"
                            console.print(f"[red]{error_msg}[/red]")
                            messages.append(
                                ToolMessage(
                                    content=error_msg,
                                    tool_call_id=tool_id,
                                    name=tool_name,
                                )
                            )
                    else:
                        error_msg = f"未知工具：{tool_name}"
                        messages.append(
                            ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_id,
                                name=tool_name,
                            )
                        )

                # 继续循环，让 LLM 基于工具结果生成最终回复

            except Exception as e:
                console.print(f"[red]Agent 错误：{e}[/red]")
                return f"抱歉，处理请求时出错：{e}", None

        # 达到最大迭代次数
        return "抱歉，工具调用次数过多，请简化您的问题。", tool_calls_made


def create_agent() -> Agent:
    """工厂函数：创建配置好的 Agent 实例"""
    from .tools import calculate, get_current_time, get_conversation_stats

    return Agent(tools=[get_current_time, calculate, get_conversation_stats])
