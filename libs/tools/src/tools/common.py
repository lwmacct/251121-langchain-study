"""
Common tool implementations

This module provides basic tools that can be used across different applications.
Tools are designed to be pure functions without side effects (no printing).
Applications should handle logging/display themselves.
"""

from datetime import datetime
from langchain_core.tools import tool


@tool
def get_current_time(timezone: str = "UTC") -> str:
    """获取当前时间。

    Args:
        timezone: 时区（例如 'UTC', 'Asia/Shanghai'）。默认为 'UTC'。

    Returns:
        当前时间的字符串表示
    """
    # 简单实现，实际项目中可以使用 pytz 库
    current_time = datetime.now()
    if timezone.lower() == "utc":
        result = f"当前 UTC 时间是: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        result = f"当前时间是: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (本地时间)"

    return result


@tool
def calculator(expression: str) -> str:
    """执行数学计算。

    Args:
        expression: 要计算的数学表达式（例如 '2 + 2', '10 * 5 + 3'）

    Returns:
        计算结果
    """
    try:
        # 使用 eval 进行计算（生产环境建议使用更安全的方法）
        # 限制 builtins 以提高安全性
        result = eval(expression, {"__builtins__": {}}, {})
        output = f"计算结果: {expression} = {result}"
        return output
    except Exception as e:
        error_msg = f"计算错误: {str(e)}"
        return error_msg


__all__ = ["get_current_time", "calculator"]
