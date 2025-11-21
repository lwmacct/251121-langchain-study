"""App6 异步意图路由模块"""

import asyncio
import json
import re
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from rich.console import Console

from .config import DEBUG

console = Console()


class RouteDecision(BaseModel):
    """路由决策"""
    action: Literal["time", "chat", "summary", "end"]
    reason: Optional[str] = None


def log_debug(title: str, content: str, style: str = "dim"):
    """DEBUG 模式下输出调试信息"""
    if DEBUG:
        console.print(f"[{style}]┌─ {title}[/{style}]")
        for line in content.split("\n"):
            console.print(f"[{style}]│ {line}[/{style}]")
        console.print(f"[{style}]└{'─' * 40}[/{style}]")


def render_history(history: list, limit: int = 10) -> str:
    """渲染历史对话"""
    lines = []
    for msg in history[-limit:]:
        if isinstance(msg, HumanMessage):
            lines.append(f"用户: {msg.content}")
        elif isinstance(msg, AIMessage):
            lines.append(f"助手: {msg.content}")
    return "\n".join(lines)


async def route_intent_async(llm: ChatOpenAI, user_text: str, history: list) -> str:
    """异步版本：使用 LLM 判断用户意图"""
    sys_msg = SystemMessage(
        content="""你是意图路由器。分析用户输入，返回一个 JSON 对象。

规则：
- time: 仅当用户询问"本地当前时间"时使用（如"现在几点"、"几点了"）
- chat: 需要 LLM 思考回答的问题（如其他时区时间、判断上午下午、解释概念等）
- summary: 用户要求总结对话
- end: 用户要结束对话（再见、退出、结束聊天）

返回格式：{"action": "time|chat|summary|end", "reason": "简短理由"}

示例：
- "现在几点" -> {"action": "time", "reason": "询问本地时间"}
- "美国现在几点" -> {"action": "chat", "reason": "需要计算其他时区"}
- "是上午还是下午" -> {"action": "chat", "reason": "需要判断时间段"}
- "总结对话" -> {"action": "summary", "reason": "用户要求总结"}
- "再见" -> {"action": "end", "reason": "用户要结束"}"""
    )
    human_msg = HumanMessage(content=f"用户输入：{user_text}\n\n请返回 JSON：")

    try:
        # 使用 ainvoke 异步调用
        resp = await llm.ainvoke([sys_msg, human_msg])
        content = resp.content.strip()
        # 提取 JSON
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            data = json.loads(json_match.group())
            action = data.get("action", "chat")
            reason = data.get("reason", "")
            if action in ["time", "chat", "summary", "end"]:
                log_debug("路由决策 (LLM)", f"action: {action}\nreason: {reason}", "cyan")
                return action
    except Exception as exc:
        log_debug("路由错误", str(exc), "red")

    # 关键词兜底（更保守）
    lower = user_text.lower()
    action = "chat"
    if user_text in ["现在几点", "几点了", "现在时间"]:
        action = "time"
    elif any(k in lower for k in ["总结对话", "概括一下"]):
        action = "summary"
    elif any(k in lower for k in ["结束聊天", "退出", "bye", "再见"]):
        action = "end"

    console.print("[bold red on yellow]⚠️  警告: LLM 路由失败，使用关键词兜底！[/bold red on yellow]")
    log_debug("路由决策 (关键词兜底)", f"action: {action}", "yellow")
    return action


# 同步版本保留兼容性
def route_intent(llm: ChatOpenAI, user_text: str, history: list) -> str:
    """同步版本：使用 LLM 判断用户意图"""
    return asyncio.get_event_loop().run_until_complete(
        route_intent_async(llm, user_text, history)
    )
