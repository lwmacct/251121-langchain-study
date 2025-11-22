"""App6 工具定义模块

优化：
1. 扩展更多工具演示
2. 更好的类型注解
3. 更详细的 docstring（LLM 用来理解工具）
"""

from datetime import datetime, timedelta, timezone
from langchain_core.tools import tool


@tool
def get_current_time() -> str:
    """获取当前的本地时间。

    当用户询问"现在几点"、"几点了"、"当前时间"时使用此工具。
    返回 UTC 时间和北京时间（UTC+8）。

    Returns:
        包含 UTC 和北京时间的字符串
    """
    utc_now = datetime.now(timezone.utc)
    beijing = utc_now.astimezone(timezone(timedelta(hours=8)))

    # 判断上午/下午
    hour = beijing.hour
    period = "上午" if 5 <= hour < 12 else ("下午" if 12 <= hour < 18 else "晚上")

    return f"UTC: {utc_now.strftime('%H:%M:%S')} | " f"北京时间: {beijing.strftime('%H:%M:%S')} ({period})"


@tool
def calculate(expression: str) -> str:
    """安全地计算数学表达式。

    当用户需要进行数学计算时使用此工具。
    支持基本运算：+、-、*、/、**（幂运算）、()（括号）

    Args:
        expression: 数学表达式，例如 "2 + 3 * 4" 或 "10 ** 2"

    Returns:
        计算结果的字符串表示

    Examples:
        calculate("2 + 3")  # "5"
        calculate("10 * (5 + 3)")  # "80"
    """
    try:
        # 安全的计算 - 只允许数字和基本运算符
        allowed_chars = set("0123456789+-*/().** ")
        if not all(c in allowed_chars for c in expression):
            return "错误：表达式包含不允许的字符"

        # 使用 eval 但限制命名空间
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"计算错误：{e}"


@tool
def get_conversation_stats(history_length: int) -> str:
    """获取当前对话的统计信息。

    当用户要求"总结对话"或"对话统计"时可以使用此工具。

    Args:
        history_length: 当前对话历史的消息数量

    Returns:
        对话统计信息
    """
    return f"当前对话包含 {history_length} 条消息。"
