"""Qdrant backend for the vector query CLI."""

from qdrant_backend import QdrantBase
from .base import BaseBackend


class QdrantBackend(QdrantBase, BaseBackend):
    """Qdrant vector database backend."""

    @property
    def backend_type(self) -> str:
        return "qdrant"
