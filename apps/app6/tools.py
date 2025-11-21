"""App6 工具定义模块"""

from datetime import datetime, timedelta, timezone
from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取当前时间，返回 UTC 和北京时间"""
    utc_now = datetime.now(timezone.utc)
    beijing = utc_now.astimezone(timezone(timedelta(hours=8)))
    return f"UTC: {utc_now.strftime('%H:%M:%S')} | 北京时间: {beijing.strftime('%H:%M:%S')}"


@tool
def end_chat(reason: str = "用户请求") -> str:
    """结束聊天会话"""
    return f"会话结束。原因：{reason}。再见！"
