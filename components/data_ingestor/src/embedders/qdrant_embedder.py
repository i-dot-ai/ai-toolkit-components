"""
Qdrant embedder for storing documents in Qdrant vector database.
"""

import hashlib
import logging
import os
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

from parsers.base import ParsedDocument
from .base import BaseEmbedder

logger = logging.getLogger(__name__)


class QdrantEmbedder(BaseEmbedder):
    """
    Embedder that stores documents in Qdrant vector database.

    Uses sentence-transformers for generating embeddings.

    Connection settings (host/port) come from environment variables.
    Behavioral settings (model_name/batch_size) come from config file.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 32
    ):
        """
        Initialize the Qdrant embedder.

        Args:
            model_name: Sentence transformer model name
            batch_size: Batch size for embedding operations
        """
        # Connection settings from environment
        self.host = os.environ.get("QDRANT_HOST", "localhost")
        self.port = int(os.environ.get("QDRANT_PORT", "6333"))

        # Behavioral settings from config
        self.model_name = model_name
        self.batch_size = batch_size

        self._client: Optional[QdrantClient] = None
        self._model: Optional[SentenceTransformer] = None

    @property
    def store_type(self) -> str:
        return "qdrant"

    @property
    def client(self) -> QdrantClient:
        """Lazy initialization of Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port)
        return self._client

    @property
    def model(self) -> SentenceTransformer:
        """Lazy initialization of embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def vector_size(self) -> int:
        """Return the embedding vector dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> list[float]:
        """
        Generate vector embedding for text.

        Args:
            text: Text content to embed

        Returns:
            Vector embedding as list of floats
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate vector embeddings for multiple texts.

        Args:
            texts: List of text content to embed

        Returns:
            List of vector embeddings
        """
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10
        )
        return embeddings.tolist()

    def ensure_collection(self, collection_name: str) -> None:
        """
        Ensure collection exists, creating it if necessary.

        Args:
            collection_name: Name of the collection
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection_name not in collection_names:
            logger.info(f"Creating collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                )
            )

    def _generate_id(self, document: ParsedDocument) -> str:
        """Generate a deterministic ID for a document based on its source."""
        return hashlib.md5(document.source.encode()).hexdigest()

    def store(
        self,
        documents: list[ParsedDocument],
        collection_name: str
    ) -> int:
        """
        Embed and store documents in Qdrant.

        Args:
            documents: List of parsed documents to embed and store
            collection_name: Name of the collection to store in

        Returns:
            Number of documents successfully stored
        """
        if not documents:
            return 0

        self.ensure_collection(collection_name)

        # Extract content for embedding
        texts = [doc.content for doc in documents]

        # Generate embeddings in batch
        logger.info(f"Generating embeddings for {len(texts)} documents...")
        embeddings = self.embed_batch(texts)

        # Prepare points for upsert
        points = []
        for doc, embedding in zip(documents, embeddings):
            point = models.PointStruct(
                id=self._generate_id(doc),
                vector=embedding,
                payload={
                    "source": doc.source,
                    "title": doc.title,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "timestamp": doc.timestamp,
                    "source_type": doc.source_type
                }
            )
            points.append(point)

        # Upsert in batches
        stored_count = 0
        for i in range(0, len(points), self.batch_size):
            batch = points[i:i + self.batch_size]
            self.client.upsert(
                collection_name=collection_name,
                points=batch
            )
            stored_count += len(batch)
            logger.info(f"Stored {stored_count}/{len(points)} documents")

        return stored_count

    def search(
        self,
        query: str,
        collection_name: str,
        limit: int = 10
    ) -> list[dict]:
        """
        Search for similar documents.

        Args:
            query: Search query text
            collection_name: Collection to search in
            limit: Maximum number of results

        Returns:
            List of matching documents with scores
        """
        query_embedding = self.embed(query)

        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit
        )

        return [
            {
                "score": hit.score,
                "source": hit.payload.get("source"),
                "title": hit.payload.get("title"),
                "content": hit.payload.get("content"),
                "metadata": hit.payload.get("metadata")
            }
            for hit in results
        ]
