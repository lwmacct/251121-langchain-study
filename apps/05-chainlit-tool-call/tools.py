"""
工具函数定义模块
包含时间查询和数学计算等工具
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
    print(f"🔧 [工具调用] get_current_time(timezone='{timezone}')")

    # 简单实现，实际项目中可以使用 pytz 库
    current_time = datetime.now()
    if timezone.lower() == "utc":
        result = f"当前 UTC 时间是: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        result = f"当前时间是: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (本地时间)"

    print(f"✅ [工具返回] {result}")
    return result


@tool
def calculator(expression: str) -> str:
    """执行数学计算。

    Args:
        expression: 要计算的数学表达式（例如 '2 + 2', '10 * 5 + 3'）

    Returns:
        计算结果
    """
    print(f"🔧 [工具调用] calculator(expression='{expression}')")

    try:
        # 使用 eval 进行计算（生产环境建议使用更安全的方法，如 ast.literal_eval 或专门的数学解析库）
        result = eval(expression, {"__builtins__": {}}, {})
        output = f"计算结果: {expression} = {result}"
        print(f"✅ [工具返回] {output}")
        return output
    except Exception as e:
        error_msg = f"计算错误: {str(e)}"
        print(f"❌ [工具错误] {error_msg}")
        return error_msg


# 导出所有工具
__all__ = ["get_current_time", "calculator"]
