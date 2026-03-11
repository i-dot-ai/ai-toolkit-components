"""
Qdrant embedder — maps ParsedDocument to the QdrantBase add_documents interface.
"""

import logging

from parsers.base import ParsedDocument
from qdrant_backend import QdrantBase
from .base import BaseEmbedder

logger = logging.getLogger(__name__)


class QdrantEmbedder(QdrantBase, BaseEmbedder):
    """
    Embedder that stores ParsedDocuments in Qdrant.

    Converts ParsedDocument fields to the dict format expected by
    QdrantBase.add_documents(), which handles embedding and upsert.
    """

    @property
    def store_type(self) -> str:
        return "qdrant"

    def store(self, documents: list[ParsedDocument], collection_name: str) -> int:
        """Convert ParsedDocuments to dicts and delegate to add_documents."""
        return self.add_documents(
            collection_name=collection_name,
            documents=[
                {
                    "content": doc.content,
                    "source": doc.source,
                    "metadata": {
                        "title": doc.title,
                        "timestamp": doc.timestamp,
                        "source_type": doc.source_type,
                        **doc.metadata,
                    },
                }
                for doc in documents
            ],
        )
