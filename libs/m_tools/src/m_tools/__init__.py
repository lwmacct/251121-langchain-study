"""
Common LangChain Tools Library

This library provides reusable tools for LangChain applications:
- get_current_time: Get current time in various timezones
- calculator: Perform mathematical calculations

Usage:
    from tools import get_current_time, calculator

    # Use in LangGraph
    from langgraph.prebuilt import ToolNode
    tool_node = ToolNode([get_current_time, calculator])

    # Use with bind_tools
    llm_with_tools = llm.bind_tools([get_current_time, calculator])
"""

from .common import get_current_time, calculator

__all__ = ["get_current_time", "calculator"]
__version__ = "0.1.0"
