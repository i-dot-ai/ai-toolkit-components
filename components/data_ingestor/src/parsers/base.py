"""
Base parser interface for data ingestion.

All parsers must inherit from BaseParser and implement the parse() method
to produce a standardized ParsedDocument output suitable for embedding.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class ParsedDocument:
    """
    Standardized document format for embedding pipelines.

    All parsers must produce documents in this format to ensure
    compatibility with downstream embedding and vector storage.
    """
    source: str          # Source identifier (URL, file path, etc.)
    title: str           # Document title
    content: str         # Main text content for embedding
    metadata: dict       # Additional metadata (source-specific)
    timestamp: str       # ISO format timestamp of parsing
    source_type: str     # Type identifier (html, pdf, markdown, etc.)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


class BaseParser(ABC):
    """
    Abstract base class for content parsers.

    Subclasses must implement:
    - parse(): Convert raw content to ParsedDocument
    - source_type property: Return the parser's source type identifier

    Optionally override:
    - fetch(): Retrieve content from a source (default returns None)
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return the source type identifier (e.g., 'html', 'pdf', 'markdown')."""
        pass

    @abstractmethod
    def parse(self, content: Any, source: str) -> ParsedDocument:
        """
        Parse raw content into a standardized document.

        Args:
            content: Raw content to parse (type depends on parser)
            source: Source identifier (URL, file path, etc.)

        Returns:
            ParsedDocument with extracted content and metadata
        """
        pass

    def fetch(self, source: str) -> Optional[Any]:
        """
        Fetch content from a source.

        Override this method for parsers that can retrieve their own content.
        Default implementation returns None (content must be provided directly).

        Args:
            source: Source identifier to fetch from

        Returns:
            Raw content or None if fetching is not supported
        """
        return None

    def ingest(self, source: str, content: Optional[Any] = None) -> Optional[ParsedDocument]:
        """
        Ingest content from a source.

        If content is not provided, attempts to fetch it using fetch().

        Args:
            source: Source identifier
            content: Optional pre-fetched content

        Returns:
            ParsedDocument or None if content could not be obtained
        """
        if content is None:
            content = self.fetch(source)
        if content is None:
            return None
        return self.parse(content, source)

    @staticmethod
    def _current_timestamp() -> str:
        """Return current time as ISO format string."""
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
