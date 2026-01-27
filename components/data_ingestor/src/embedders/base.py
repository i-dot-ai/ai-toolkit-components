"""
Base embedder interface for vector storage.

All embedders must inherit from BaseEmbedder and implement the methods
to generate embeddings and store them in a vector database.
"""

from abc import ABC, abstractmethod
from typing import Optional

from parsers.base import ParsedDocument


class BaseEmbedder(ABC):
    """
    Abstract base class for embedding and storing documents.

    Subclasses must implement:
    - embed(): Generate vector embeddings for text
    - store(): Store documents with embeddings in vector database
    - store_type property: Return the embedder's storage type identifier
    """

    @property
    @abstractmethod
    def store_type(self) -> str:
        """Return the storage type identifier (e.g., 'qdrant', 'pinecone')."""
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Generate vector embedding for text.

        Args:
            text: Text content to embed

        Returns:
            Vector embedding as list of floats
        """
        pass

    @abstractmethod
    def store(
        self,
        documents: list[ParsedDocument],
        collection_name: str
    ) -> int:
        """
        Embed and store documents in the vector database.

        Args:
            documents: List of parsed documents to embed and store
            collection_name: Name of the collection to store in

        Returns:
            Number of documents successfully stored
        """
        pass

    def embed_and_store(
        self,
        documents: list[ParsedDocument],
        collection_name: str
    ) -> int:
        """
        Convenience method to embed and store documents.

        Args:
            documents: List of parsed documents
            collection_name: Target collection name

        Returns:
            Number of documents successfully stored
        """
        return self.store(documents, collection_name)
