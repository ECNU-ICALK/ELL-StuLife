"""
Core tool interface and management for CampusLifeBench
All natural language communications/returns MUST use English only
"""

from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
import inspect


class ToolResultStatus(Enum):
    """Status of tool execution"""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


@dataclass
class ToolResult:
    """
    Unified interface for all tool results in CampusLifeBench
    All message content MUST be in English only
    """
    status: ToolResultStatus
    message: str  # MUST be in English - natural language description for Agent
    data: Optional[Dict[str, Any]] = None  # Optional structured data
    error_code: Optional[str] = None  # Error code for debugging
    
    @classmethod
    def success(cls, message: str, data: Optional[Dict[str, Any]] = None) -> "ToolResult":
        """Create a successful tool result"""
        return cls(status=ToolResultStatus.SUCCESS, message=message, data=data)
    
    @classmethod
    def failure(cls, message: str, error_code: Optional[str] = None) -> "ToolResult":
        """Create a failed tool result"""
        return cls(status=ToolResultStatus.FAILURE, message=message, error_code=error_code)
    
    @classmethod
    def error(cls, message: str, error_code: Optional[str] = None) -> "ToolResult":
        """Create an error tool result"""
        return cls(status=ToolResultStatus.ERROR, message=message, error_code=error_code)
    
    def is_success(self) -> bool:
        """Check if the tool execution was successful"""
        return self.status == ToolResultStatus.SUCCESS
    
    def is_failure(self) -> bool:
        """Check if the tool execution failed"""
        return self.status == ToolResultStatus.FAILURE
    
    def is_error(self) -> bool:
        """Check if the tool execution had an error"""
        return self.status == ToolResultStatus.ERROR


class ToolManager:
    """
    Static class for generating and managing tool definitions
    Generates tools.json for Agent consumption
    """
    
    @staticmethod
    def extract_tool_info(method) -> Dict[str, Any]:
        """
        Extract tool information from a method using reflection
        Returns tool definition in standardized format
        """
        signature = inspect.signature(method)
        docstring = inspect.getdoc(method) or ""
        
        # Parse parameters
        parameters = {}
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
                
            param_info = {
                "type": "string",  # Default type
                "required": param.default == inspect.Parameter.empty,
                "description": f"Parameter {param_name}"
            }
            
            # Try to extract type information
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_info["type"] = "string"
                elif param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif hasattr(param.annotation, '__origin__'):
                    # Handle generic types like Dict, List, etc.
                    param_info["type"] = "object"
            
            parameters[param_name] = param_info
        
        return {
            "name": method.__name__,
            "description": docstring.split('\n')[0] if docstring else f"Tool: {method.__name__}",
            "parameters": parameters
        }
    
    @staticmethod
    def generate_tools_json(environment_instance) -> str:
        """
        Generate tools.json by reflecting on CampusEnvironment methods
        Returns JSON string with all available tools
        """
        tools = []
        
        # Get all public methods from the environment
        for attr_name in dir(environment_instance):
            if not attr_name.startswith('_'):
                attr = getattr(environment_instance, attr_name)
                if callable(attr) and hasattr(attr, '__self__'):
                    # This is a bound method
                    tool_info = ToolManager.extract_tool_info(attr)
                    tools.append(tool_info)
        
        return json.dumps({"tools": tools}, indent=2)
    
    @staticmethod
    def save_tools_json(environment_instance, filepath: str) -> None:
        """
        Save tools.json file for Agent consumption
        """
        tools_json = ToolManager.generate_tools_json(environment_instance)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(tools_json)


def validate_english_only(text: str) -> bool:
    """
    Validate that text contains only English characters and common symbols
    This is a basic validation - in production, more sophisticated checks could be used
    """
    if not text:
        return True
    
    # First check: reject any non-ASCII characters (Unicode > 127)
    for char in text:
        if ord(char) > 127:
            return False

    # Second check: only allow specific English characters
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?;:()[]{}"\'-_@#$%^&*+=<>/\\|`~\n\t')

    # Check each character is in allowed set
    for char in text:
        if char not in allowed_chars:
            return False

    return True


def ensure_english_message(message: str) -> str:
    """
    Ensure message is in English only
    Raises ValueError if non-English characters detected
    """
    if not validate_english_only(message):
        raise ValueError("All natural language communications must be in English only")
    return message
