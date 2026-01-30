"""
Unit tests for the data_ingestor component.

Tests parsers, embedders, and the ingestor orchestrator using mocks
so no Docker or external services are needed.
"""

import sys
import os
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch, call

import pytest
import numpy as np

# Add data_ingestor src to path so we can import directly
_src = str(Path(__file__).resolve().parents[2] / "components" / "data_ingestor" / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Mock heavy dependencies that aren't installed locally (fastembed, qdrant_client).
# These must be set before importing the embedders package.
_mock_fastembed = ModuleType("fastembed")
_mock_fastembed.TextEmbedding = MagicMock
sys.modules.setdefault("fastembed", _mock_fastembed)

_mock_qdrant = ModuleType("qdrant_client")
_mock_qdrant.QdrantClient = MagicMock
sys.modules.setdefault("qdrant_client", _mock_qdrant)

_mock_qdrant_models = ModuleType("qdrant_client.models")
_mock_qdrant_models.Distance = MagicMock()
_mock_qdrant_models.Distance.COSINE = "Cosine"
_mock_qdrant_models.VectorParams = MagicMock
_mock_qdrant_models.PointStruct = MagicMock
sys.modules.setdefault("qdrant_client.models", _mock_qdrant_models)

from parsers.base import ParsedDocument
from parsers.html_parser import HTMLParser


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html>
<head><title>Test Page</title>
<meta name="description" content="A test page">
<meta name="keywords" content="test,unit">
<meta property="og:title" content="OG Test">
</head>
<body>
<nav>Navigation</nav>
<header>Header</header>
<main>
<h1>Main Heading</h1>
<p>Main content paragraph.</p>
</main>
<footer>Footer</footer>
<script>alert('x')</script>
<style>body{}</style>
</body>
</html>
"""


def _make_doc(source="https://example.com", content="test content"):
    return ParsedDocument(
        source=source, title="Test", content=content,
        metadata={}, timestamp="2025-01-01T00:00:00Z", source_type="html",
    )


# ---------------------------------------------------------------------------
# HTMLParser
# ---------------------------------------------------------------------------

class TestHTMLParser:
    def test_parse_extracts_all_fields(self):
        """Parse sample HTML and verify title, content, metadata, and excluded elements."""
        parser = HTMLParser()
        doc = parser.parse(SAMPLE_HTML, "https://example.com/page")

        assert doc.source_type == "html"
        assert doc.source == "https://example.com/page"
        assert doc.timestamp
        assert doc.title == "Test Page"
        assert "Main content paragraph." in doc.content
        for excluded in ("Navigation", "Footer", "alert"):
            assert excluded not in doc.content
        assert doc.metadata["domain"] == "example.com"
        assert doc.metadata["path"] == "/page"
        assert doc.metadata["description"] == "A test page"
        assert doc.metadata["keywords"] == "test,unit"
        assert doc.metadata["og_title"] == "OG Test"

    def test_title_fallback_to_h1(self):
        doc = HTMLParser().parse(
            "<html><body><h1>Heading</h1><p>Content</p></body></html>",
            "https://example.com",
        )
        assert doc.title == "Heading"

    def test_custom_exclude_elements(self):
        doc = HTMLParser(exclude_elements=["p"]).parse(SAMPLE_HTML, "https://example.com")
        assert "Main content paragraph." not in doc.content

    def test_fetch_success_and_failure(self):
        import requests
        parser = HTMLParser()

        with patch.object(parser.session, "get") as mock_get:
            mock_resp = MagicMock(text="<html><body>OK</body></html>")
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            assert parser.fetch("https://example.com") == "<html><body>OK</body></html>"

        with patch.object(parser.session, "get", side_effect=requests.RequestException("fail")):
            assert parser.fetch("https://bad-url.com") is None

    def test_ingest_with_and_without_content(self):
        parser = HTMLParser()
        doc = parser.ingest("https://example.com", content=SAMPLE_HTML)
        assert doc is not None and doc.title == "Test Page"

        with patch.object(parser, "fetch", return_value=None):
            assert parser.ingest("https://bad-url.com") is None

    def test_extract_links_absolute_and_relative(self):
        html = """
        <html><body>
        <a href="https://example.com/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="sub/page3">Page 3</a>
        </body></html>
        """
        links = HTMLParser.extract_links(html, "https://example.com/docs/")
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert "https://example.com/docs/sub/page3" in links

    def test_extract_links_strips_fragments(self):
        html = '<html><body><a href="/page#section">Link</a></body></html>'
        links = HTMLParser.extract_links(html, "https://example.com/")
        assert links == ["https://example.com/page"]

    def test_extract_links_ignores_non_http(self):
        html = """
        <html><body>
        <a href="mailto:test@example.com">Email</a>
        <a href="javascript:void(0)">JS</a>
        <a href="ftp://files.example.com">FTP</a>
        <a href="https://example.com/valid">Valid</a>
        </body></html>
        """
        links = HTMLParser.extract_links(html, "https://example.com/")
        assert links == ["https://example.com/valid"]

    def test_extract_links_deduplicates(self):
        html = """
        <html><body>
        <a href="/page">Link 1</a>
        <a href="/page">Link 2</a>
        <a href="/page#section">Link 3</a>
        </body></html>
        """
        links = HTMLParser.extract_links(html, "https://example.com/")
        assert links == ["https://example.com/page"]


# ---------------------------------------------------------------------------
# Plugin registries (auto-discovery)
# ---------------------------------------------------------------------------

class TestRegistries:
    def test_parser_registry(self):
        from parsers import get_parser_class, supported_types
        assert "html" in supported_types()
        assert get_parser_class("html") is HTMLParser
        with pytest.raises(ValueError, match="Unsupported source type"):
            get_parser_class("nonexistent")

    def test_embedder_registry(self):
        from embedders import supported_stores, get_embedder_class
        assert "qdrant" in supported_stores()
        with pytest.raises(ValueError, match="Unknown store type"):
            get_embedder_class("nonexistent")


# ---------------------------------------------------------------------------
# QdrantEmbedder (mocked - no Qdrant or FastEmbed needed)
# ---------------------------------------------------------------------------

class TestQdrantEmbedder:
    @patch.dict(os.environ, {"VECTOR_DB_HOST": "myhost", "VECTOR_DB_PORT": "1234"})
    def test_init_from_env(self):
        from embedders.qdrant_embedder import QdrantEmbedder
        embedder = QdrantEmbedder()
        assert embedder.host == "myhost"
        assert embedder.port == 1234
        assert embedder.store_type == "qdrant"

    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    def test_store_creates_collection_and_upserts(self, MockTextEmbedding, MockQdrantClient):
        from embedders.qdrant_embedder import QdrantEmbedder

        mock_model = MagicMock()
        mock_model.embed.side_effect = [
            [np.array([0.1, 0.2, 0.3])],  # _ensure_collection test embedding
            [np.array([0.1, 0.2, 0.3])],  # actual embedding
        ]
        MockTextEmbedding.return_value = mock_model

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQdrantClient.return_value = mock_client

        assert QdrantEmbedder().store([_make_doc()], "new-col") == 1
        mock_client.create_collection.assert_called_once()
        mock_client.upsert.assert_called_once()

    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    def test_store_skips_collection_creation_if_exists(self, MockTextEmbedding, MockQdrantClient):
        from embedders.qdrant_embedder import QdrantEmbedder

        MockTextEmbedding.return_value = MagicMock(
            embed=MagicMock(return_value=[np.array([0.1, 0.2, 0.3])])
        )
        existing = MagicMock()
        existing.name = "existing"
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[existing])
        MockQdrantClient.return_value = mock_client

        QdrantEmbedder().store([_make_doc()], "existing")
        mock_client.create_collection.assert_not_called()

    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    def test_store_batches_upserts(self, MockTextEmbedding, MockQdrantClient):
        from embedders.qdrant_embedder import QdrantEmbedder

        mock_model = MagicMock()
        mock_model.embed.side_effect = [
            [np.array([0.1, 0.2, 0.3])],                          # _ensure_collection
            [np.array([0.1, 0.2, 0.3]) for _ in range(5)],        # actual
        ]
        MockTextEmbedding.return_value = mock_model

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQdrantClient.return_value = mock_client

        docs = [_make_doc(source=f"https://example.com/{i}") for i in range(5)]
        assert QdrantEmbedder(batch_size=2).store(docs, "col") == 5
        assert mock_client.upsert.call_count == 3  # 2+2+1


# ---------------------------------------------------------------------------
# DataIngestor orchestrator
# ---------------------------------------------------------------------------

class TestDataIngestor:
    @patch("parsers.html_parser.HTMLParser.fetch")
    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    def test_ingest_end_to_end(self, MockTextEmbedding, MockQdrantClient, mock_fetch):
        from ingestor import DataIngestor

        mock_fetch.return_value = SAMPLE_HTML
        MockTextEmbedding.return_value = MagicMock(
            embed=MagicMock(side_effect=[
                [np.array([0.1, 0.2, 0.3])],
                [np.array([0.1, 0.2, 0.3])],
            ])
        )
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQdrantClient.return_value = mock_client

        ingestor = DataIngestor(config_path="/nonexistent/config.yaml")
        count = ingestor.ingest(["https://example.com"], source_type="html",
                                store_type="qdrant", collection="test")

        assert count == 1
        mock_fetch.assert_called_once_with("https://example.com")
        mock_client.upsert.assert_called_once()

    def test_ingest_failed_parse_returns_zero(self):
        from ingestor import DataIngestor
        ingestor = DataIngestor(config_path="/nonexistent/config.yaml")
        with patch.object(ingestor, "get_parser") as mock_gp:
            mock_gp.return_value = MagicMock(ingest=MagicMock(return_value=None))
            assert ingestor.ingest(["https://bad.com"]) == 0

    def test_config_loading(self, tmp_path):
        import yaml
        from ingestor import DataIngestor

        # Missing file -> empty config
        assert DataIngestor(config_path="/nonexistent/config.yaml").config == {}

        # Valid file
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"request_delay": 2.0, "html": {"timeout": 10}}))
        ingestor = DataIngestor(config_path=str(config_file))
        assert ingestor.config["request_delay"] == 2.0
        assert ingestor.config["html"]["timeout"] == 10


# ---------------------------------------------------------------------------
# Crawl functionality
# ---------------------------------------------------------------------------

SEED_HTML = """
<html><body>
<p>Seed page content</p>
<a href="https://example.com/docs/page1">Page 1</a>
<a href="https://example.com/docs/page2">Page 2</a>
<a href="https://example.com/other/page3">Other section</a>
<a href="https://external.com/page">External</a>
</body></html>
"""

CHILD_HTML = """
<html><body>
<p>Child page content</p>
<a href="https://example.com/docs/page1/sub">Sub page</a>
</body></html>
"""


class TestCrawl:
    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    @patch("parsers.html_parser.HTMLParser.fetch")
    def test_crawl_follows_same_prefix_links(self, mock_fetch, MockTE, MockQC):
        from ingestor import DataIngestor

        mock_fetch.side_effect = lambda url: {
            "https://example.com/docs/": SEED_HTML,
            "https://example.com/docs/page1": CHILD_HTML,
            "https://example.com/docs/page2": CHILD_HTML,
        }.get(url)

        MockTE.return_value = MagicMock(
            embed=MagicMock(return_value=[np.array([0.1, 0.2, 0.3])])
        )
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQC.return_value = mock_client

        ingestor = DataIngestor(config_path="/nonexistent/config.yaml")
        count = ingestor.crawl(
            ["https://example.com/docs/"],
            max_depth=1, collection="test"
        )

        # Seed + 2 children under /docs/ (not /other/ or external)
        assert count == 3
        fetched_urls = [c.args[0] for c in mock_fetch.call_args_list]
        assert "https://example.com/docs/" in fetched_urls
        assert "https://example.com/docs/page1" in fetched_urls
        assert "https://example.com/docs/page2" in fetched_urls
        assert "https://example.com/other/page3" not in fetched_urls
        assert "https://external.com/page" not in fetched_urls

    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    @patch("parsers.html_parser.HTMLParser.fetch")
    def test_crawl_respects_depth_limit(self, mock_fetch, MockTE, MockQC):
        from ingestor import DataIngestor

        mock_fetch.side_effect = lambda url: {
            "https://example.com/docs/": SEED_HTML,
            "https://example.com/docs/page1": CHILD_HTML,
            "https://example.com/docs/page2": CHILD_HTML,
            "https://example.com/docs/page1/sub": CHILD_HTML,
        }.get(url)

        MockTE.return_value = MagicMock(
            embed=MagicMock(return_value=[np.array([0.1, 0.2, 0.3])])
        )
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQC.return_value = mock_client

        ingestor = DataIngestor(config_path="/nonexistent/config.yaml")

        # depth=0: seed only
        count = ingestor.crawl(["https://example.com/docs/"], max_depth=0, collection="t")
        assert count == 1

    @patch("embedders.qdrant_embedder.QdrantClient")
    @patch("embedders.qdrant_embedder.TextEmbedding")
    @patch("parsers.html_parser.HTMLParser.fetch")
    def test_crawl_deduplicates_urls(self, mock_fetch, MockTE, MockQC):
        from ingestor import DataIngestor

        # Both pages link to each other
        html_a = '<html><body><a href="https://example.com/docs/b">B</a></body></html>'
        html_b = '<html><body><a href="https://example.com/docs/a">A</a></body></html>'
        mock_fetch.side_effect = lambda url: {
            "https://example.com/docs/a": html_a,
            "https://example.com/docs/b": html_b,
        }.get(url)

        MockTE.return_value = MagicMock(
            embed=MagicMock(return_value=[np.array([0.1, 0.2, 0.3])])
        )
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQC.return_value = mock_client

        ingestor = DataIngestor(config_path="/nonexistent/config.yaml")
        count = ingestor.crawl(
            ["https://example.com/docs/a"],
            max_depth=5, collection="t"
        )

        # Only 2 pages despite circular links and high depth
        assert count == 2
        assert mock_fetch.call_count == 2
