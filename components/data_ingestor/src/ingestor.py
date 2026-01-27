"""
Data Ingestor - Ingests content, converts to JSON, and embeds into vector databases.

This module provides a generic ingestion framework that uses pluggable parsers
to handle different content types (HTML, PDF, Markdown, etc.) and embedders
to store the resulting documents in vector databases.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

import yaml

from parsers import BaseParser, ParsedDocument, get_parser_class, supported_types
from embedders import BaseEmbedder, get_embedder_class, supported_stores

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DataIngestor:
    """
    Generic data ingestor that uses pluggable parsers and embedders.

    Supports multiple content types through parser classes and multiple
    vector databases through embedder classes.
    """

    def __init__(self, config_path: str = "/app/config/config.yaml"):
        self.config = self._load_config(config_path)
        self._parsers: dict[str, BaseParser] = {}
        self._embedders: dict[str, BaseEmbedder] = {}

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return {}

    def get_parser(self, source_type: str) -> BaseParser:
        """
        Get or create a parser for the given source type.

        Args:
            source_type: Parser type identifier (e.g., 'html', 'pdf')

        Returns:
            Configured parser instance

        Raises:
            ValueError: If source type is not supported
        """
        if source_type not in self._parsers:
            parser_class = get_parser_class(source_type)
            parser_config = self.config.get(source_type, {})
            self._parsers[source_type] = parser_class(**parser_config)

        return self._parsers[source_type]

    def get_embedder(self, store_type: str) -> BaseEmbedder:
        """
        Get or create an embedder for the given store type.

        Args:
            store_type: Embedder type identifier (e.g., 'qdrant')

        Returns:
            Configured embedder instance

        Raises:
            ValueError: If store type is not supported
        """
        if store_type not in self._embedders:
            embedder_class = get_embedder_class(store_type)
            embedder_config = self.config.get(store_type, {})
            self._embedders[store_type] = embedder_class(**embedder_config)

        return self._embedders[store_type]

    def ingest(
        self,
        source: str,
        source_type: str = "html",
        content: Optional[str] = None
    ) -> Optional[ParsedDocument]:
        """
        Ingest content from a source.

        Args:
            source: Source identifier (URL, file path, etc.)
            source_type: Type of parser to use
            content: Optional pre-fetched content

        Returns:
            ParsedDocument or None on failure
        """
        parser = self.get_parser(source_type)
        return parser.ingest(source, content)

    def ingest_batch(
        self,
        sources: list[str],
        source_type: str = "html"
    ) -> list[ParsedDocument]:
        """
        Ingest multiple sources.

        Args:
            sources: List of source identifiers
            source_type: Type of parser to use for all sources

        Returns:
            List of ParsedDocuments
        """
        results = []
        delay = self.config.get("request_delay", 1.0)

        for source in sources:
            result = self.ingest(source, source_type)
            if result:
                results.append(result)
            time.sleep(delay)

        return results

    def ingest_and_embed(
        self,
        sources: list[str],
        source_type: str = "html",
        store_type: str = "qdrant",
        collection_name: str = "documents"
    ) -> int:
        """
        Ingest sources and embed them into a vector database.

        Args:
            sources: List of source identifiers
            source_type: Type of parser to use
            store_type: Type of vector store to use
            collection_name: Name of the collection to store in

        Returns:
            Number of documents successfully stored
        """
        documents = self.ingest_batch(sources, source_type)
        if not documents:
            logger.warning("No documents were successfully ingested")
            return 0

        embedder = self.get_embedder(store_type)
        stored = embedder.store(documents, collection_name)
        logger.info(f"Successfully embedded and stored {stored} documents")
        return stored

    @staticmethod
    def supported_types() -> list[str]:
        """Return list of supported source types."""
        return supported_types()

    @staticmethod
    def supported_stores() -> list[str]:
        """Return list of supported store types."""
        return supported_stores()


def main():
    """Main entry point for the data ingestor."""
    import argparse

    parser = argparse.ArgumentParser(description="Data ingestor for embedding pipelines")
    parser.add_argument("--source", help="Single source to ingest (URL, file path, etc.)")
    parser.add_argument("--sources-file", help="File containing sources (one per line)")
    parser.add_argument("--type", "-t", default="html",
                        help=f"Source type (default: html, available: {DataIngestor.supported_types()})")
    parser.add_argument("--output", "-o", help="Output JSON file path (if not embedding)")
    parser.add_argument("--config", default="/app/config/config.yaml",
                        help="Config file path")

    # Embedding options
    parser.add_argument("--embed", action="store_true",
                        help="Embed documents into vector database")
    parser.add_argument("--store", "-s", default="qdrant",
                        help=f"Vector store type (default: qdrant, available: {DataIngestor.supported_stores()})")
    parser.add_argument("--collection", "-c", default="documents",
                        help="Collection name for vector store (default: documents)")

    args = parser.parse_args()

    ingestor = DataIngestor(config_path=args.config)

    sources = []
    if args.source:
        sources.append(args.source)
    if args.sources_file:
        with open(args.sources_file) as f:
            sources.extend(line.strip() for line in f if line.strip())

    if not sources:
        logger.info("No sources provided. Running in standby mode.")
        while True:
            time.sleep(60)

    logger.info(f"Ingesting {len(sources)} source(s) as {args.type}...")

    if args.embed:
        # Ingest and embed into vector database
        stored = ingestor.ingest_and_embed(
            sources,
            source_type=args.type,
            store_type=args.store,
            collection_name=args.collection
        )
        logger.info(f"Embedded {stored} documents into {args.store}/{args.collection}")
    else:
        # Ingest and output to JSON file
        documents = ingestor.ingest_batch(sources, source_type=args.type)
        output_path = Path(args.output or "/app/output/documents.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump([doc.to_dict() for doc in documents], f, indent=2)

        logger.info(f"Wrote {len(documents)} documents to {output_path}")


if __name__ == "__main__":
    main()
