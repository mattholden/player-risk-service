"""
Base Tool Class

Provides the abstract base class for all custom tools. Tools wrap
functionality that LLM agents can call during their reasoning process.

Each tool defines:
- name: Identifier used by the LLM
- description: Explains to the LLM when to use this tool
- parameters: JSON schema for expected arguments
- execute(): The actual implementation
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import json

from xai_sdk.tools import chat_pb2
from xai_sdk.chat import tool


class BaseTool(ABC):
    """
    Abstract base class for custom LLM tools.
    
    Subclasses must implement:
    - name: Tool identifier
    - description: What the tool does (shown to LLM)
    - parameters: JSON schema for arguments
    - execute(): The actual implementation
    
    Example:
        class MyTool(BaseTool):
            @property
            def name(self) -> str:
                return "my_tool"
            
            @property
            def description(self) -> str:
                return "Does something useful"
            
            @property
            def parameters(self) -> dict:
                return {
                    "type": "object",
                    "properties": {
                        "arg1": {"type": "string"}
                    },
                    "required": ["arg1"]
                }
            
            def execute(self, arg1: str) -> str:
                return json.dumps({"result": arg1})
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name used by the LLM to call this tool.
        
        Should be snake_case, descriptive, e.g., "get_active_roster"
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Description shown to the LLM.
        
        Should clearly explain:
        - What the tool does
        - When to use it
        - What it returns
        """
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        JSON schema for tool parameters.
        
        Standard JSON Schema format with:
        - type: "object"
        - properties: dict of parameter definitions
        - required: list of required parameter names
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with given arguments.
        
        Args:
            **kwargs: Arguments matching the parameters schema
            
        Returns:
            JSON string with results (must be serializable)
        """
        pass
    
    def to_protobuf(self) -> chat_pb2.Tool:
        """
        Convert this tool to xAI SDK protobuf format.
        
        Returns:
            chat_pb2.Tool protobuf object
        """
        tool = chat_pb2.Tool()
        tool.function.name = self.name
        tool.function.description = self.description
        tool.function.parameters = json.dumps(self.parameters)
        return tool

    def to_client_side_tool(self) -> tool:
        """
        Convert this tool to xAI SDK client-side tool format.
        
        Returns:
            xai_sdk.chat.tool object
        """
        return tool(
            name=self.name, 
            description=self.description, 
            parameters=self.parameters
            )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"

