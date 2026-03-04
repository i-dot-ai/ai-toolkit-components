"""List query - list all collections."""

from backends.base import BaseBackend

from .base import BaseQuery


class ListQuery(BaseQuery):
    """List all collections in the vector database."""

    @property
    def query_name(self) -> str:
        return "list"

    @property
    def description(self) -> str:
        return "List all collections"

    @property
    def input_schema(self) -> dict:
        return {"properties": {}, "required": []}

    def execute(self, backend: BaseBackend, **kwargs) -> list[str]:
        return backend.list_collections()

    def format_output(self, result, json_output: bool = False) -> None:
        for name in result:
            print(name)
