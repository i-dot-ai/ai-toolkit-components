"""Delete query - delete a collection."""

from backends.base import BaseBackend

from .base import BaseQuery


class DeleteQuery(BaseQuery):
    """Delete an entire collection from the vector database."""

    @property
    def query_name(self) -> str:
        return "delete"

    @property
    def description(self) -> str:
        return "Delete a collection"

    @property
    def input_schema(self) -> dict:
        return {
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Collection name to delete",
                },
            },
            "required": ["collection"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        backend.delete_collection(collection_name=kwargs["collection"])
        return {"collection": kwargs["collection"]}

    def format_output(self, result, json_output: bool = False) -> None:
        print(f"Deleted collection '{result['collection']}'")
