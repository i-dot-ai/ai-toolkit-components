"""List collections tool - enumerate available collections."""

from backends.base import BaseBackend
from .base import BaseTool


class ListCollectionsTool(BaseTool):
    """List all available collections in the vector database."""

    @property
    def tool_name(self) -> str:
        return "list_collections"

    @property
    def description(self) -> str:
        return "List all available collections in the vector database"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
        }

    def execute(self, backend: BaseBackend, **kwargs) -> list[str]:
        return backend.list_collections()
