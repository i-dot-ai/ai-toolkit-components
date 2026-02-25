"""
Data Ingestor - Ingests content and embeds into vector databases.

This module provides a generic ingestion framework that uses pluggable parsers
to handle different content types (HTML, PDF, Markdown, etc.) and embedders
to store the resulting documents in vector databases.
"""

import logging
import time
from pathlib import Path

import yaml

from parsers import BaseParser, ParsedDocument, get_parser_class, available_parsers
from embedders import BaseEmbedder, get_embedder_class, available_embedders

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
        self.parsers = self._init_parsers()
        self.embedders = self._init_embedders()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded config from {config_path} ({len(config)} keys)")
            return config
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return {}

    def _init_parsers(self) -> dict[str, BaseParser]:
        """Initialise all supported parsers."""
        parsers = {}
        for source_type in available_parsers:
            parser_class = get_parser_class(source_type)
            parser_config = self.config.get(source_type, {})
            logger.info(f"Creating parser: {parser_class.__name__} (type={source_type})")
            parsers[source_type] = parser_class(**parser_config)
        return parsers

    def _init_embedders(self) -> dict[str, BaseEmbedder]:
        """Initialise all supported embedders."""
        embedders = {}
        for store_type in available_embedders:
            embedder_class = get_embedder_class(store_type)
            embedder_config = self.config.get(store_type, {})
            logger.info(f"Creating embedder: {embedder_class.__name__} (store={store_type})")
            embedders[store_type] = embedder_class(**embedder_config)
        return embedders

    @staticmethod
    def detect_source_type(source: str) -> str:
        """Detect source type from file extension, defaulting to 'html' for URLs."""
        path = source.split("://")[-1].split("?")[0].split("/")[-1]
        ext = Path(path).suffix.lstrip(".").lower()

        # Common TLDs that shouldn't be treated as file extensions
        tlds = ["com", "org", "net", "edu", "gov", "io", "co", "uk", "de", "fr", "jp", "au", "ca"]

        if not ext or ext in tlds:
            return "html"
        return ext

    def ingest(
        self,
        sources: list[str],
        source_type: str | None = None,
        store_type: str = "qdrant",
        collection: str = "documents"
    ) -> int:
        """
        Ingest sources and embed them into a vector database.

        Args:
            sources: List of source identifiers (URLs, file paths, etc.)
            source_type: Type of parser to use (auto-detected from extension if None)
            store_type: Type of vector store to use
            collection: Name of the collection to store in

        Returns:
            Number of documents successfully stored
        """
        logger.info(f"Starting ingestion: {len(sources)} source(s), "
                    f"type={source_type or 'auto'}, store={store_type}, collection={collection}")
        delay = self.config.get("request_delay", 1.0)

        documents = []
        for i, source in enumerate(sources):
            # Rate limit: delay between requests to avoid hammering servers
            if i > 0:
                time.sleep(delay)
            detected_type = source_type or self.detect_source_type(source)
            try:
                parser = self.parsers[detected_type]
                logger.info(f"Parsing ({detected_type}): {source}")
                docs = parser.ingest(source)
                documents.extend(docs)
            except KeyError:
                logger.warning(
                    f"No parser for type '{detected_type}'. "
                    f"Available: {list(self.parsers.keys())}"
                )
            except Exception as e:
                logger.warning(f"Failed to ingest {source}. Error: {e}")

        if not documents:
            logger.warning("No documents were successfully parsed")
            return 0

        logger.info(f"Storing {len(documents)} document(s) into {store_type}/{collection}")
        embedder = self.embedders[store_type]
        stored = embedder.store(documents, collection)
        logger.info(f"Successfully stored {stored} document(s)")
        return stored


def main():
    """Main entry point for the data ingestor."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest content and embed into vector database",
        usage="%(prog)s [options] <source> [source ...]"
    )
    parser.add_argument("sources", nargs="*", help="Sources to ingest (URLs, file paths, etc.)")
    parser.add_argument("-f", "--file", help="File containing sources (one per line)")
    parser.add_argument("-t", "--type", default=None,
                        help="Source type (auto-detected from extension if not specified)")
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
            file_sources = [line.strip() for line in f if line.strip()]
        logger.info(f"Loaded {len(file_sources)} source(s) from {args.file}")
        sources.extend(file_sources)

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
