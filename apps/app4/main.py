from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Iterable, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

DEBUG = os.getenv("APP4_DEBUG") == "1"


@tool
def calc(expression: str) -> str:
    """计算表达式，支持 + - * / () 与 math 函数（如 sqrt、sin、log）。"""
    allowed = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
    try:
        value = eval(expression, {"__builtins__": {}}, allowed)
    except Exception as exc:  # noqa: BLE001
        return f"计算出错: {exc}"
    return str(value)


@tool
def now() -> str:
    """返回当前时间（UTC 与北京时间 UTC+8）。"""
    utc_now = datetime.now(timezone.utc)
    beijing = utc_now.astimezone(timezone(timedelta(hours=8)))
    return f"UTC: {utc_now.isoformat()} | Beijing: {beijing.isoformat()}"


@tool
def end_session(reason: str | None = None) -> str:
    """结束会话并致谢。"""
    base = "本次对话结束。"
    if reason:
        base += f" 原因：{reason}。"
    return base + " 欢迎随时再来。"


def get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        return api_key

    # 兼容 .taskfile/.env 本地存放
    env_file = Path(__file__).resolve().parents[2] / ".taskfile" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                os.environ["OPENROUTER_API_KEY"] = api_key
                return api_key

    raise RuntimeError("请先在环境变量 OPENROUTER_API_KEY 中配置 OpenRouter API Key")


def build_llm(model: str, temperature: float = 0, max_tokens: int | None = 1024) -> ChatOpenAI:
    api_key = get_api_key()
    model_id = os.getenv("APP4_MODEL", model)
    return ChatOpenAI(
        model=model_id,
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def render_recent(history: list[SystemMessage | HumanMessage | AIMessage | ToolMessage], limit: int = 12) -> str:
    displayed: list[str] = []
    for msg in history[-limit:]:
        if isinstance(msg, HumanMessage):
            displayed.append(f"用户: {msg.content}")
        elif isinstance(msg, AIMessage):
            displayed.append(f"助手: {msg.content}")
        elif isinstance(msg, ToolMessage):
            displayed.append(f"工具: {msg.content}")
    return "\n".join(displayed)


def summarize_history_llm(llm: ChatOpenAI, history: list[SystemMessage | HumanMessage | AIMessage | ToolMessage]) -> str:
    sys_msg = SystemMessage(content="你是对话总结助手，用 2-3 句中文概述主要问题和结论，保持简洁。不要添加新信息。")
    human_msg = HumanMessage(content=f"对话片段：\n{render_recent(history)}")
    try:
        resp = llm.invoke([sys_msg, human_msg])
        return resp.content if isinstance(resp, AIMessage) else str(resp)
    except Exception as exc:  # noqa: BLE001
        return f"总结失败：{exc}"


class RouteDecision(BaseModel):
    action: Literal["time", "calc", "summary", "end", "chat"]
    reason: Optional[str] = None
    expression: Optional[str] = None


def route_intent(
    router_llm: ChatOpenAI, user_text: str, history: list[SystemMessage | HumanMessage | AIMessage | ToolMessage]
) -> tuple[str, Optional[str]]:
    """使用结构化输出选择动作：time|calc|summary|end|chat"""
    sys_msg = SystemMessage(
        content=(
            "你是意图路由器。根据用户需求选择动作并返回 JSON。"
            "时间/日期/上午下午 => time；数学/公式 => calc；总结对话 => summary；结束/再见 => end；其他 => chat。"
        )
    )
    human_msg = HumanMessage(content=f"用户输入：{user_text}\n上下文片段：\n{render_recent(history)}")
    parser_llm = router_llm.with_structured_output(RouteDecision)
    try:
        decision: RouteDecision = parser_llm.invoke([sys_msg, human_msg])
        if DEBUG:
            print(f"[router decision] {decision}")
        return decision.action, decision.expression
    except Exception as exc:  # noqa: BLE001
        if DEBUG:
            print(f"[router error] {exc}")
        action = "chat"
        expr = None

    # 若结构化路由失败或返回 chat，使用轻量关键词兜底以避免工具缺失
    if action == "chat":
        lower = user_text.lower()
        if any(k in lower for k in ["时间", "几点", "am", "pm", "上午", "下午"]):
            action = "time"
        elif any(k in lower for k in ["算", "计算", "+", "-", "*", "/"]):
            action = "calc"
        elif any(k in lower for k in ["总结", "概括", "summary"]):
            action = "summary"
        elif any(k in lower for k in ["结束", "退出", "bye", "再见"]):
            action = "end"

    return action, expr


def interactive_chat() -> None:
    print("Hello from app4! 交互式问答（LLM 决策工具）。输入空行或 Ctrl+C 退出。")

    default_model = os.getenv("APP4_MODEL", "openai/gpt-4o-mini")
    llm_router = build_llm(default_model, temperature=0, max_tokens=512)
    llm_chat = build_llm(default_model, temperature=0.2, max_tokens=1024)

    history: list[SystemMessage | HumanMessage | AIMessage | ToolMessage] = []
    last_time_text: str | None = None
    last_period: str | None = None

    interactive = sys.stdin.isatty()
    piped_iter: Iterable[str] | None = None
    if not interactive:
        piped_iter = iter([line.strip() for line in sys.stdin.read().splitlines() if line.strip()])

    while True:
        try:
            if interactive:
                query = input("\n用户: ").strip()
            else:
                query = next(piped_iter)  # type: ignore[arg-type]
                print(f"\n用户: {query}")
        except StopIteration:
            break
        except (KeyboardInterrupt, EOFError):
            print("\n结束对话。")
            break

        if not query:
            print("结束对话。")
            break

        history.append(HumanMessage(content=query))

        action, expression = route_intent(llm_router, query, history)

        if action == "time":
            result = now.invoke({})
            beijing_now = datetime.now(timezone(timedelta(hours=8)))
            hour = beijing_now.hour
            if hour < 6:
                period = "凌晨"
            elif hour < 12:
                period = "上午"
            elif hour < 18:
                period = "下午"
            else:
                period = "晚上"
            time_text = beijing_now.strftime("%Y-%m-%d %H:%M:%S")
            last_time_text = time_text
            last_period = period
            tool_msg = ToolMessage(tool_call_id="now", content=result)
            history.append(tool_msg)
            print(f"[tool] now -> {result}")
            # 让 LLM 基于工具结果自然表述
            prompt = SystemMessage(
                content="你是中文助手，请结合工具返回的时间信息，用自然口吻回答用户，可简述时段（上午/下午/晚上）并引用时间，不必生硬。"
            )
            try:
                resp = llm_chat.invoke([prompt] + history[-6:])  # 限制上下文长度
                reply = resp.content if isinstance(resp, AIMessage) else str(resp)
            except Exception as exc:  # noqa: BLE001
                reply = f"现在是{period}，北京时间 {time_text} (UTC+8)。"
                if DEBUG:
                    print(f"[error] time llm failed: {exc}")
            history.append(AIMessage(content=reply))
            print(f"助手: {reply}")
            continue

        if action == "calc":
            expr = expression or query
            result = calc.invoke({"expression": expr})
            tool_msg = ToolMessage(tool_call_id="calc", content=str(result))
            history.append(tool_msg)
            print(f"[tool] calc expr={expr} -> {result}")
            prompt = SystemMessage(content="你是中文助手，请用简短中文给出计算结果，必要时解释。")
            try:
                resp = llm_chat.invoke([prompt] + history[-6:])
                reply = resp.content if isinstance(resp, AIMessage) else str(resp)
            except Exception as exc:  # noqa: BLE001
                reply = f"计算结果：{result}"
                if DEBUG:
                    print(f"[error] calc llm failed: {exc}")
            history.append(AIMessage(content=reply))
            print(f"助手: {reply}")
            continue

        if action == "summary":
            summary = summarize_history_llm(llm_chat, history)
            history.append(AIMessage(content=summary))
            print(f"助手: {summary}")
            continue

        # 若路由到聊天，但问题涉及上午/下午且有最近时间记录，则直接回答
        if action == "chat" and any(k in query for k in ["上午", "下午", "am", "pm"]):
            if last_period and last_time_text:
                reply = f"根据刚才的时间记录，现在是{last_period}（北京时间 {last_time_text}）。"
            else:
                reply = "暂时没有时间记录，请先问我现在几点。"
            history.append(AIMessage(content=reply))
            print(f"助手: {reply}")
            continue

        if action == "end":
            farewell = end_session.invoke({"reason": query})
            history.append(ToolMessage(tool_call_id="end_session", content=farewell))
            history.append(AIMessage(content=farewell))
            print(f"助手: {farewell}")
            break

        # 默认聊天
        try:
            resp = llm_chat.invoke(history)
            reply = resp.content if isinstance(resp, AIMessage) else str(resp)
        except Exception as exc:  # noqa: BLE001
            reply = f"对话失败：{exc}"
        history.append(AIMessage(content=reply))
        print(f"助手: {reply}")


def main() -> None:
    interactive_chat()


if __name__ == "__main__":
    main()
