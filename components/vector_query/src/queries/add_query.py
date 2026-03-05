"""Add query - add a document to a collection."""

import json

from backends.base import BaseBackend

from .base import BaseQuery


class AddQuery(BaseQuery):
    """Add a document with text and optional metadata to a collection."""

    @property
    def query_name(self) -> str:
        return "add"

    @property
    def description(self) -> str:
        return "Add a document to a collection"

    @property
    def input_schema(self) -> dict:
        return {
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Collection name",
                },
                "text": {
                    "type": "string",
                    "description": "Document text to embed and store",
                },
                "metadata": {
                    "type": "string",
                    "description": "Optional metadata as a JSON string (e.g. '{\"key\": \"val\"}')",
                },
            },
            "required": ["collection", "text"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        metadata = {}
        if kwargs.get("metadata"):
            metadata = json.loads(kwargs["metadata"])
        documents = [{"text": kwargs["text"], "metadata": metadata}]
        count = backend.add_documents(
            collection_name=kwargs["collection"],
            documents=documents,
        )
        return {"stored_count": count}

    def format_output(self, result, json_output: bool = False) -> None:
        print(f"Stored {result['stored_count']} document(s)")
