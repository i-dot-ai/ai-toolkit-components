"""
Tools package - pluggable MCP tool implementations.

Tools are auto-discovered from this package. Any class inheriting
from BaseTool is automatically registered by its tool_name property.
"""

from pathlib import Path

from registry import PluginRegistry

from .base import BaseTool

_registry = PluginRegistry(BaseTool, "tool_name", "tool")
_registry.discover(__name__, Path(__file__).parent)

get_tool_class = _registry.get
available_tools = _registry.supported_keys()

__all__ = [
    "BaseTool",
    "get_tool_class",
    "available_tools",
]
