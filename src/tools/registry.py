"""
Tool Registry

Central registry for managing all available tools. Provides:
- Tool registration and lookup
- Conversion to protobuf format for xAI SDK
- Tool execution by name
"""

from typing import Dict, List, Optional
import json

from src.tools.base import BaseTool


class ToolRegistry:
    """
    Central registry for all available tools.
    
    Usage:
        registry = ToolRegistry()
        registry.register(ActiveRosterTool())
        
        # Get tools for chat.create()
        tools = registry.get_all_protobufs()
        
        # Execute a tool by name
        result = registry.execute("get_active_roster", {"team": "Arsenal"})
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        print(f"🔧 Registered tool: {tool.name}")
    
    def unregister(self, name: str) -> bool:
        """
        Remove a tool from the registry.
        
        Args:
            name: Tool name to remove
            
        Returns:
            True if tool was removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def get_all(self) -> List[BaseTool]:
        """
        Get all registered tools.
        
        Returns:
            List of all tool instances
        """
        return list(self._tools.values())
    
    def get_all_protobufs(self) -> List:
        """
        Get all tools as protobuf objects for chat.create().
        
        Returns:
            List of chat_pb2.Tool protobuf objects
        """
        return [tool.to_protobuf() for tool in self._tools.values()]

    def get_all_client_side_tools(self) -> List:
        """
        Get all tools that can be executed client-side.
        
        Returns:
            List of tool names
        """
        return [tool.to_client_side_tool() for tool in self._tools.values()]
    
    def get_tool_names(self) -> List[str]:
        """
        Get names of all registered tools.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def execute(self, name: str, arguments: Dict) -> str:
        """
        Execute a tool by name with given arguments.
        
        Args:
            name: Tool name
            arguments: Dict of arguments to pass to the tool
            
        Returns:
            JSON string with results or error
        """
        tool = self._tools.get(name)
        
        if not tool:
            return json.dumps({
                "error": f"Unknown tool: {name}",
                "available_tools": list(self._tools.keys())
            })
        
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return json.dumps({
                "error": f"Tool execution failed: {str(e)}",
                "tool": name,
                "arguments": arguments
            })
    
    def clear(self) -> None:
        """Remove all tools from the registry."""
        self._tools.clear()
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __repr__(self) -> str:
        return f"<ToolRegistry(tools={list(self._tools.keys())})>"


# Global registry instance - can be used across agents
tool_registry = ToolRegistry()

