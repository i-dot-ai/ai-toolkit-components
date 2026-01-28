"""
Data Ingestor - Ingests content and embeds into vector databases.

This module provides a generic ingestion framework that uses pluggable parsers
to handle different content types (HTML, PDF, Markdown, etc.) and embedders
to store the resulting documents in vector databases.
"""

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

    def __init__(self, config_path: str = "/app/custom/config/config.yaml"):
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
        """Get or create a parser for the given source type."""
        if source_type not in self._parsers:
            parser_class = get_parser_class(source_type)
            parser_config = self.config.get(source_type, {})
            self._parsers[source_type] = parser_class(**parser_config)
        return self._parsers[source_type]

    def get_embedder(self, store_type: str) -> BaseEmbedder:
        """Get or create an embedder for the given store type."""
        if store_type not in self._embedders:
            embedder_class = get_embedder_class(store_type)
            embedder_config = self.config.get(store_type, {})
            self._embedders[store_type] = embedder_class(**embedder_config)
        return self._embedders[store_type]

    def ingest(
        self,
        sources: list[str],
        source_type: str = "html",
        store_type: str = "qdrant",
        collection: str = "documents"
    ) -> int:
        """
        Ingest sources and embed them into a vector database.

        Args:
            sources: List of source identifiers (URLs, file paths, etc.)
            source_type: Type of parser to use
            store_type: Type of vector store to use
            collection: Name of the collection to store in

        Returns:
            Number of documents successfully stored
        """
        parser = self.get_parser(source_type)
        delay = self.config.get("request_delay", 1.0)

        documents = []
        for source in sources:
            logger.info(f"Parsing: {source}")
            doc = parser.ingest(source)
            if doc:
                documents.append(doc)
            if len(sources) > 1:
                time.sleep(delay)

        if not documents:
            logger.warning("No documents were successfully parsed")
            return 0

        logger.info(f"Embedding {len(documents)} document(s) into {store_type}/{collection}")
        embedder = self.get_embedder(store_type)
        stored = embedder.store(documents, collection)
        logger.info(f"Successfully stored {stored} document(s)")
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

    parser = argparse.ArgumentParser(
        description="Ingest content and embed into vector database",
        usage="%(prog)s [options] <source> [source ...]"
    )
    parser.add_argument("sources", nargs="*", help="Sources to ingest (URLs, file paths, etc.)")
    parser.add_argument("-f", "--file", help="File containing sources (one per line)")
    parser.add_argument("-t", "--type", default="html",
                        help="Source type (default: html)")
    parser.add_argument("-s", "--store", default="qdrant",
                        help="Vector store type (default: qdrant)")
    parser.add_argument("-c", "--collection", default="documents",
                        help="Collection name (default: documents)")
    parser.add_argument("--config", default="/app/custom/config/config.yaml",
                        help="Config file path")

    args = parser.parse_args()

    ingestor = DataIngestor(config_path=args.config)

    # Collect sources from args and file
    sources = list(args.sources)
    if args.file:
        with open(args.file) as f:
            sources.extend(line.strip() for line in f if line.strip())

    if not sources:
        parser.print_help()
        return

    stored = ingestor.ingest(
        sources,
        source_type=args.type,
        store_type=args.store,
        collection=args.collection
    )

    logger.info(f"Done. Ingested {stored} document(s).")


if __name__ == "__main__":
    main()
