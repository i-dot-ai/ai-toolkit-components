"""Get documents tool - retrieve documents from a collection."""

from backends.base import BaseBackend
from .base import BaseTool


class GetDocumentsTool(BaseTool):
    """Retrieve documents from a collection with pagination."""

    @property
    def tool_name(self) -> str:
        return "get_documents"

    @property
    def description(self) -> str:
        return "Retrieve documents from a collection with optional pagination"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to return",
                    "default": 10,
                },
                "offset": {
                    "type": "string",
                    "description": "Pagination offset from a previous request",
                },
            },
            "required": ["collection_name"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        return backend.get_documents(
            collection_name=kwargs["collection_name"],
            limit=kwargs.get("limit", 10),
            offset=kwargs.get("offset"),
        )
