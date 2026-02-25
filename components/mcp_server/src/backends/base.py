"""
Base class for vector database backends.

Backends abstract the connection and operations for different vector
databases. Each backend is auto-discovered by the PluginRegistry via
its backend_type property.
"""

from abc import ABC, abstractmethod


class BaseBackend(ABC):
    """Abstract base class for vector database backends."""

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return the backend type identifier (e.g., 'qdrant')."""
        ...

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""
        ...

    @abstractmethod
    def search(
        self, collection_name: str, query_text: str, limit: int = 10
    ) -> list[dict]:
        """
        Search for documents by semantic similarity.

        Args:
            collection_name: Name of the collection to search.
            query_text: The search query text.
            limit: Maximum number of results to return.

        Returns:
            List of result dicts with 'id', 'score', and 'payload' keys.
        """
        ...

    @abstractmethod
    def list_collections(self) -> list[str]:
        """Return names of all collections."""
        ...

    @abstractmethod
    def get_documents(
        self, collection_name: str, limit: int = 10, offset: str | None = None
    ) -> dict:
        """
        Retrieve documents from a collection.

        Args:
            collection_name: Name of the collection.
            limit: Maximum number of documents to return.
            offset: Pagination offset (backend-specific).

        Returns:
            Dict with 'documents' list and 'next_offset' for pagination.
        """
        ...

    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete an entire collection.

        Returns:
            True if the collection was deleted successfully.
        """
        ...

    @abstractmethod
    def add_documents(
        self, collection_name: str, documents: list[dict]
    ) -> int:
        """
        Add documents to a collection.

        Each document dict should have 'text' and optionally 'metadata'.

        Args:
            collection_name: Name of the collection.
            documents: List of dicts with 'text' and optional 'metadata'.

        Returns:
            Number of documents successfully stored.
        """
        ...
