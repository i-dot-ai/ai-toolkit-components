"""Qdrant backend for the MCP server."""

from qdrant_backend import QdrantBase
from .base import BaseBackend


class QdrantBackend(QdrantBase, BaseBackend):
    """Qdrant vector database backend."""

    @property
    def backend_type(self) -> str:
        return "qdrant"
