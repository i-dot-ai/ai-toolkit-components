"""Search query - semantic similarity search over a collection."""

import json

from backends.base import BaseBackend

from .base import BaseQuery


class SearchQuery(BaseQuery):
    """Search for documents by semantic similarity."""

    @property
    def query_name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for documents by semantic similarity"

    @property
    def input_schema(self) -> dict:
        return {
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text",
                },
                "collection": {
                    "type": "string",
                    "description": "Collection name",
                    "default": "documents",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10,
                },
            },
            "required": ["query"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> list[dict]:
        return backend.search(
            collection_name=kwargs["collection"],
            query_text=kwargs["query"],
            limit=kwargs.get("limit", 10),
        )

    def format_output(self, result, json_output: bool = False) -> None:
        for item in result:
            if json_output:
                print(json.dumps(item, default=str))
            else:
                score = item["score"]
                text = item["payload"].get("text", "")
                snippet = text[:200].replace("\n", " ")
                print(f"[score={score:.2f}] {snippet}")
