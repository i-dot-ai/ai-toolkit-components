"""Get query - retrieve documents from a collection."""

import json
import sys

from backends.base import BaseBackend

from .base import BaseQuery


class GetQuery(BaseQuery):
    """Retrieve documents from a collection with optional pagination."""

    @property
    def query_name(self) -> str:
        return "get"

    @property
    def description(self) -> str:
        return "Retrieve documents from a collection"

    @property
    def input_schema(self) -> dict:
        return {
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Collection name",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents",
                    "default": 10,
                },
                "offset": {
                    "type": "string",
                    "description": "Pagination offset token from a previous get call",
                },
            },
            "required": ["collection"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        return backend.get_documents(
            collection_name=kwargs["collection"],
            limit=kwargs.get("limit", 10),
            offset=kwargs.get("offset"),
        )

    def format_output(self, result, json_output: bool = False) -> None:
        for doc in result["documents"]:
            print(json.dumps(doc["payload"], default=str))
        if result["next_offset"]:
            print(f"# next_offset: {result['next_offset']}", file=sys.stderr)
