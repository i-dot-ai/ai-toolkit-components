"""
Base class for vector query CLI commands.

Each subclass defines its subcommand name, help text, input schema, and
execute logic. The input schema is used to auto-generate argparse flags —
no argparse code is needed in the subclass.
"""

import json
from abc import ABC, abstractmethod

from backends.base import BaseBackend


class BaseQuery(ABC):
    """Abstract base class for CLI query commands."""

    @property
    @abstractmethod
    def query_name(self) -> str:
        """
        Unique name used as the CLI subcommand (e.g. 'search').

        Must be unique across all registered queries.
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Help text shown in --help output."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """
        JSON Schema describing the command's parameters.

        Each property becomes a --name CLI flag. Properties listed in
        'required' become mandatory flags; others are optional.

        Supported types: 'string', 'integer', 'boolean'.
        Use 'default' for optional parameters.

        Example:
            {
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                        "default": "documents",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 10,
                    },
                },
                "required": [],
            }
        """
        ...

    @abstractmethod
    def execute(self, backend: BaseBackend, **kwargs):
        """
        Run the query against the backend.

        Args:
            backend: Connected vector database backend instance.
            **kwargs: Parsed CLI arguments matching input_schema properties.

        Returns:
            Result data passed to format_output.
        """
        ...

    def format_output(self, result, json_output: bool = False) -> None:
        """
        Print result to stdout.

        Override to customise output formatting. Default: one JSON object
        per line for lists, or a single JSON object for dicts.

        Args:
            result: Return value from execute().
            json_output: True if the user passed --json.
        """
        if result is None:
            return
        if isinstance(result, list):
            for item in result:
                print(json.dumps(item, default=str))
        elif isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result, default=str))
