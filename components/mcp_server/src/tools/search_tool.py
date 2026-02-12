"""Search tool - semantic similarity search over a collection."""

from backends.base import BaseBackend
from .base import BaseTool


class SearchTool(BaseTool):
    """Search for documents by semantic similarity."""

    @property
    def tool_name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for documents by semantic similarity in a collection"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection to search",
                },
                "query": {
                    "type": "string",
                    "description": "Search query text",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 10,
                },
            },
            "required": ["collection_name", "query"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> list[dict]:
        return backend.search(
            collection_name=kwargs["collection_name"],
            query_text=kwargs["query"],
            limit=kwargs.get("limit", 10),
        )
