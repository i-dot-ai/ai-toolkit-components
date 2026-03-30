"""
Shared Qdrant base class for components that read from or write to Qdrant.

Provides connection management, collection lifecycle, embedding model
initialisation, all standard database operations, deterministic document ID
generation, and input validation. Components that interact with Qdrant should
inherit from QdrantBase rather than duplicate this boilerplate.
"""

import hashlib
import logging
import os
import re
import time
from typing import Optional

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MAX_CONNECT_RETRIES = 30
RETRY_DELAY_SECONDS = 2

_COLLECTION_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class QdrantBase:
    """
    Shared base for Qdrant-backed components.

    Subclasses inherit connection management, embedding model initialisation,
    collection lifecycle, deterministic ID generation, and input validation.
    Connection settings (host/port) come from environment variables;
    behavioural settings (model_name/batch_size) come from the config file.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        batch_size: int = 32,
    ):
        self.host = os.environ.get("VECTOR_DB_HOST", "localhost")
        self.port = int(os.environ.get("VECTOR_DB_PORT", "6333"))
        self.model_name = model_name
        self.batch_size = batch_size

        self._client: Optional[QdrantClient] = None
        self._embedding_model: Optional[TextEmbedding] = None

        logger.info(
            f"{self.__class__.__name__} initialised: host={self.host}, port={self.port}, "
            f"model={self.model_name}, batch_size={self.batch_size}"
        )

    @property
    def client(self) -> QdrantClient:
        """Lazy initialisation of Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port)
        return self._client

    @property
    def embedding_model(self) -> TextEmbedding:
        """Lazy initialisation of FastEmbed model."""
        if self._embedding_model is None:
            logger.info(f"Loading FastEmbed model: {self.model_name}")
            self._embedding_model = TextEmbedding(model_name=self.model_name)
        return self._embedding_model

    def connect(self) -> None:
        """Connect to Qdrant with retry logic."""
        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            try:
                self.client.get_collections()
                logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
                return
            except Exception as e:
                if attempt == MAX_CONNECT_RETRIES:
                    raise ConnectionError(
                        f"Failed to connect to Qdrant at {self.host}:{self.port} "
                        f"after {MAX_CONNECT_RETRIES} attempts: {e}"
                    )
                logger.warning(
                    f"Connection attempt {attempt}/{MAX_CONNECT_RETRIES} failed: {e}. "
                    f"Retrying in {RETRY_DELAY_SECONDS}s..."
                )
                time.sleep(RETRY_DELAY_SECONDS)

    def _ensure_collection(self, collection_name: str) -> None:
        """Ensure collection exists, creating it if necessary."""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection_name in collection_names:
            return

        test_embedding = list(self.embedding_model.embed(["test"]))[0]
        vector_size = len(test_embedding)

        logger.info(
            f"Creating collection '{collection_name}' "
            f"(model: {self.model_name}, dimensions: {vector_size})"
        )
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def is_healthy(self) -> bool:
        """Return True if the Qdrant backend is reachable and operational."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    @staticmethod
    def generate_document_id(source: str) -> str:
        """Generate a deterministic document ID from a source identifier.

        Uses the document source (URL, file path, or other stable identifier)
        so that re-ingesting the same source via any component always produces
        the same ID, enabling correct upserts rather than duplicates.
        """
        return hashlib.md5(source.encode()).hexdigest()

    def _validate_collection_name(self, name: str, check_exists: bool = True) -> None:
        """Validate a Qdrant collection name.

        Raises:
            ValueError: If the name is empty or contains characters outside
                [a-zA-Z0-9_-], does not start with an alphanumeric character,
                or (when check_exists=True) the collection does not exist.
        """
        if not name:
            raise ValueError("Collection name must not be empty.")
        if not _COLLECTION_NAME_RE.match(name):
            raise ValueError(
                f"Invalid collection name '{name}'. "
                "Collection names must start with a letter or digit and may "
                "only contain letters, digits, hyphens, and underscores."
            )
        if check_exists:
            existing = [c.name for c in self.client.get_collections().collections]
            if name not in existing:
                raise ValueError(f"Collection '{name}' does not exist.")

    def search(
        self, collection_name: str, query_text: str, limit: int = 10
    ) -> list[dict]:
        """Search for documents by semantic similarity."""
        self._validate_collection_name(collection_name)

        query_embedding = list(self.embedding_model.embed([query_text]))[0]

        response = self.client.query_points(
            collection_name=collection_name,
            query=query_embedding.tolist(),
            limit=limit,
        )

        return [
            {
                "id": str(point.id),
                "score": point.score,
                "payload": point.payload,
            }
            for point in response.points
        ]

    def list_collections(self) -> list[str]:
        """Return names of all collections."""
        collections = self.client.get_collections().collections
        return [c.name for c in collections]

    def get_documents(
        self, collection_name: str, limit: int = 10, offset: str | None = None
    ) -> dict:
        """Retrieve documents from a collection using scroll."""
        self._validate_collection_name(collection_name)

        results, next_offset = self.client.scroll(
            collection_name=collection_name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        return {
            "documents": [
                {"id": str(point.id), "payload": point.payload}
                for point in results
            ],
            "next_offset": str(next_offset) if next_offset else None,
        }

    def delete_collection(self, collection_name: str) -> bool:
        """Delete an entire collection."""
        self._validate_collection_name(collection_name)

        self.client.delete_collection(collection_name=collection_name)
        logger.info(f"Deleted collection '{collection_name}'")
        return True

    def add_documents(
        self, collection_name: str, documents: list[dict]
    ) -> int:
        """Add documents to a collection with automatic embedding."""
        self._validate_collection_name(collection_name, check_exists=False)

        if not documents:
            return 0

        for i, doc in enumerate(documents):
            if not doc.get("content", "").strip():
                raise ValueError(f"Document at index {i} has empty or missing 'content'.")
            if not doc.get("source", "").strip():
                raise ValueError(f"Document at index {i} has empty or missing 'source'.")

        self._ensure_collection(collection_name)

        texts = [doc["content"] for doc in documents]
        embeddings = list(self.embedding_model.embed(texts))

        points = []
        for doc, embedding in zip(documents, embeddings):
            points.append(PointStruct(
                id=self.generate_document_id(doc["source"]),
                vector=embedding.tolist(),
                payload={
                    "source": doc["source"],
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                },
            ))

        stored_count = 0
        for i in range(0, len(points), self.batch_size):
            batch = points[i : i + self.batch_size]
            self.client.upsert(collection_name=collection_name, points=batch)
            stored_count += len(batch)

        logger.info(f"Stored {stored_count} documents in '{collection_name}'")
        return stored_count
