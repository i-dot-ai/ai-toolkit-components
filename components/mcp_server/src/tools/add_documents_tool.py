"""Add documents tool - insert documents into a collection."""

from backends.base import BaseBackend
from .base import BaseTool


class AddDocumentsTool(BaseTool):
    """Add documents with text and optional metadata to a collection."""

    @property
    def tool_name(self) -> str:
        return "add_documents"

    @property
    def description(self) -> str:
        return (
            "Add documents to a collection. Each document should have "
            "'text' and optionally 'metadata'"
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection",
                },
                "documents": {
                    "type": "array",
                    "description": "List of documents to add",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Document text content",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Optional metadata",
                            },
                        },
                        "required": ["text"],
                    },
                },
            },
            "required": ["collection_name", "documents"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        count = backend.add_documents(
            collection_name=kwargs["collection_name"],
            documents=kwargs["documents"],
        )
        return {"stored_count": count}
