"""
Tools package - Custom tools for LLM agents.

This package provides:
- BaseTool: Abstract base class for defining tools
- ToolRegistry: Central registry for managing tools
- Concrete tool implementations (roster, etc.)

Usage:
    from src.tools import tool_registry, ActiveRosterTool
    
    # Register tools
    tool_registry.register(ActiveRosterTool())
    
    # Use with GrokClient
    response = grok_client.chat_with_tools(
        messages=messages,
        tool_registry=tool_registry
    )
"""

from src.tools.base import BaseTool
from src.tools.registry import ToolRegistry, tool_registry
from src.tools.roster_tool import ActiveRosterTool

__all__ = [
    'BaseTool',
    'ToolRegistry',
    'tool_registry',
    'ActiveRosterTool',
]

