"""
Base class for MCP tools.

Each tool subclass defines its MCP metadata (name, description, input
schema) and an execute method. Tools are auto-discovered by the
PluginRegistry via their tool_name property.
"""

import inspect
import json
from abc import ABC, abstractmethod
from typing import Any

from backends.base import BaseBackend


class BaseTool(ABC):
    """Abstract base class for MCP tools."""

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Unique tool name for MCP registration."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the MCP tool."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """JSON Schema dict describing the tool's input parameters."""
        ...

    @abstractmethod
    def execute(self, backend: BaseBackend, **kwargs) -> Any:
        """
        Execute the tool using the given backend.

        Args:
            backend: The vector database backend instance.
            **kwargs: Arguments from the MCP tool call.

        Returns:
            Result data (will be serialised to JSON for the MCP response).
        """
        ...

    def as_handler(self, backend: BaseBackend):
        """Return a callable with an explicit signature for FastMCP registration."""
        properties = self.input_schema.get("properties", {})
        required = set(self.input_schema.get("required", []))

        params = [
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                default=inspect.Parameter.empty if name in required else prop.get("default"),
            )
            for name, prop in properties.items()
        ]

        def handler(**kwargs) -> str:
            result = self.execute(backend, **kwargs)
            return json.dumps(result, default=str)

        handler.__name__ = self.tool_name
        handler.__doc__ = self.description
        handler.__signature__ = inspect.Signature(params)
        return handler
