"""
Queries package - pluggable CLI query commands.

Queries are auto-discovered from this package. Any class inheriting
from BaseQuery is automatically registered by its query_name property.
"""

from pathlib import Path

from registry import PluginRegistry

from .base import BaseQuery

_registry = PluginRegistry(BaseQuery, "query_name", "query")
_registry.discover(__name__, Path(__file__).parent)

get_query_class = _registry.get
available_queries = _registry.supported_keys()

__all__ = [
    "BaseQuery",
    "get_query_class",
    "available_queries",
]
