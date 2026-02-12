"""Delete collection tool - remove an entire collection."""

from backends.base import BaseBackend
from .base import BaseTool


class DeleteCollectionTool(BaseTool):
    """Delete an entire collection from the vector database."""

    @property
    def tool_name(self) -> str:
        return "delete_collection"

    @property
    def description(self) -> str:
        return "Delete an entire collection and all its documents"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection to delete",
                },
            },
            "required": ["collection_name"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        success = backend.delete_collection(
            collection_name=kwargs["collection_name"],
        )
        return {"deleted": success}
