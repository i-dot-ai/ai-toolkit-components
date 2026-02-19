"""
Unit tests for the mcp_server component.

Tests backends, tools, and the server orchestrator using mocks
so no Docker or external services are needed.
"""

import sys
import os
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
import numpy as np

# Add mcp_server src to path so we can import directly
_src = str(Path(__file__).resolve().parents[2] / "components" / "mcp_server" / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Mock heavy dependencies that aren't installed locally.
# These must be set before importing the backends/tools packages.
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


# ---------------------------------------------------------------------------
# Backend tests
# ---------------------------------------------------------------------------

class TestQdrantBackend:
    @patch.dict(os.environ, {"VECTOR_DB_HOST": "myhost", "VECTOR_DB_PORT": "1234"})
    def test_init_from_env(self):
        from backends.qdrant_backend import QdrantBackend
        backend = QdrantBackend()
        assert backend.host == "myhost"
        assert backend.port == 1234
        assert backend.backend_type == "qdrant"

    @patch("backends.qdrant_backend.QdrantClient")
    def test_connect_success(self, MockQdrantClient):
        from backends.qdrant_backend import QdrantBackend
        mock_client = MagicMock()
        MockQdrantClient.return_value = mock_client
        backend = QdrantBackend()
        backend.connect()
        mock_client.get_collections.assert_called_once()

    @patch("backends.qdrant_backend.QdrantClient")
    @patch("backends.qdrant_backend.TextEmbedding")
    def test_search(self, MockTextEmbedding, MockQdrantClient):
        from backends.qdrant_backend import QdrantBackend

        mock_model = MagicMock()
        mock_model.embed.return_value = [np.array([0.1, 0.2, 0.3])]
        MockTextEmbedding.return_value = mock_model

        mock_hit = MagicMock()
        mock_hit.id = "abc"
        mock_hit.score = 0.95
        mock_hit.payload = {"text": "test content"}

        mock_response = MagicMock()
        mock_response.points = [mock_hit]

        mock_client = MagicMock()
        mock_client.query_points.return_value = mock_response
        MockQdrantClient.return_value = mock_client

        backend = QdrantBackend()
        results = backend.search("test-col", "query text", limit=5)

        assert len(results) == 1
        assert results[0]["id"] == "abc"
        assert results[0]["score"] == 0.95
        mock_client.query_points.assert_called_once()

    @patch("backends.qdrant_backend.QdrantClient")
    def test_list_collections(self, MockQdrantClient):
        from backends.qdrant_backend import QdrantBackend

        col1 = MagicMock()
        col1.name = "collection-a"
        col2 = MagicMock()
        col2.name = "collection-b"
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[col1, col2])
        MockQdrantClient.return_value = mock_client

        backend = QdrantBackend()
        result = backend.list_collections()
        assert result == ["collection-a", "collection-b"]

    @patch("backends.qdrant_backend.QdrantClient")
    def test_get_documents(self, MockQdrantClient):
        from backends.qdrant_backend import QdrantBackend

        point = MagicMock()
        point.id = "doc1"
        point.payload = {"text": "content"}

        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point], None)
        MockQdrantClient.return_value = mock_client

        backend = QdrantBackend()
        result = backend.get_documents("test-col", limit=5)

        assert len(result["documents"]) == 1
        assert result["documents"][0]["id"] == "doc1"
        assert result["next_offset"] is None

    @patch("backends.qdrant_backend.QdrantClient")
    def test_delete_collection(self, MockQdrantClient):
        from backends.qdrant_backend import QdrantBackend

        mock_client = MagicMock()
        MockQdrantClient.return_value = mock_client

        backend = QdrantBackend()
        assert backend.delete_collection("test-col") is True
        mock_client.delete_collection.assert_called_once_with(collection_name="test-col")

    @patch("backends.qdrant_backend.QdrantClient")
    @patch("backends.qdrant_backend.TextEmbedding")
    def test_add_documents(self, MockTextEmbedding, MockQdrantClient):
        from backends.qdrant_backend import QdrantBackend

        mock_model = MagicMock()
        mock_model.embed.side_effect = [
            [np.array([0.1, 0.2, 0.3])],  # _ensure_collection test embedding
            [np.array([0.1, 0.2, 0.3])],  # actual embedding
        ]
        MockTextEmbedding.return_value = mock_model

        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        MockQdrantClient.return_value = mock_client

        backend = QdrantBackend()
        count = backend.add_documents("test-col", [{"text": "hello world"}])

        assert count == 1
        mock_client.create_collection.assert_called_once()
        mock_client.upsert.assert_called_once()


# ---------------------------------------------------------------------------
# Plugin registries (auto-discovery)
# ---------------------------------------------------------------------------

class TestRegistries:
    def test_backend_registry(self):
        from backends import available_backends, get_backend_class
        from backends.qdrant_backend import QdrantBackend
        assert "qdrant" in available_backends
        assert get_backend_class("qdrant") is QdrantBackend
        with pytest.raises(ValueError, match="Unknown backend"):
            get_backend_class("nonexistent")

    def test_tool_registry(self):
        from tools import available_tools, get_tool_class
        expected_tools = [
            "search", "list_collections", "get_documents",
            "delete_collection", "add_documents",
        ]
        for tool_name in expected_tools:
            assert tool_name in available_tools
            assert get_tool_class(tool_name) is not None
        with pytest.raises(ValueError, match="Unknown tool"):
            get_tool_class("nonexistent")


# ---------------------------------------------------------------------------
# Tool classes
# ---------------------------------------------------------------------------

class TestTools:
    def _make_mock_backend(self):
        backend = MagicMock()
        backend.search.return_value = [{"id": "1", "score": 0.9, "payload": {}}]
        backend.list_collections.return_value = ["col1", "col2"]
        backend.get_documents.return_value = {"documents": [], "next_offset": None}
        backend.delete_collection.return_value = True
        backend.add_documents.return_value = 2
        return backend

    def test_search_tool(self):
        from tools.search_tool import SearchTool
        tool = SearchTool()
        assert tool.tool_name == "search"
        assert "collection_name" in tool.input_schema["properties"]
        assert "query" in tool.input_schema["properties"]

        backend = self._make_mock_backend()
        result = tool.execute(backend, collection_name="col", query="test", limit=5)
        backend.search.assert_called_once_with(
            collection_name="col", query_text="test", limit=5
        )
        assert len(result) == 1

    def test_list_collections_tool(self):
        from tools.list_collections_tool import ListCollectionsTool
        tool = ListCollectionsTool()
        assert tool.tool_name == "list_collections"

        backend = self._make_mock_backend()
        result = tool.execute(backend)
        backend.list_collections.assert_called_once()
        assert result == ["col1", "col2"]

    def test_get_documents_tool(self):
        from tools.get_documents_tool import GetDocumentsTool
        tool = GetDocumentsTool()
        assert tool.tool_name == "get_documents"

        backend = self._make_mock_backend()
        result = tool.execute(backend, collection_name="col", limit=5)
        backend.get_documents.assert_called_once_with(
            collection_name="col", limit=5, offset=None
        )

    def test_delete_collection_tool(self):
        from tools.delete_collection_tool import DeleteCollectionTool
        tool = DeleteCollectionTool()
        assert tool.tool_name == "delete_collection"

        backend = self._make_mock_backend()
        result = tool.execute(backend, collection_name="col")
        backend.delete_collection.assert_called_once_with(collection_name="col")
        assert result == {"deleted": True}

    def test_add_documents_tool(self):
        from tools.add_documents_tool import AddDocumentsTool
        tool = AddDocumentsTool()
        assert tool.tool_name == "add_documents"

        docs = [{"text": "hello"}, {"text": "world"}]
        backend = self._make_mock_backend()
        result = tool.execute(backend, collection_name="col", documents=docs)
        backend.add_documents.assert_called_once_with(
            collection_name="col", documents=docs
        )
        assert result == {"stored_count": 2}


# ---------------------------------------------------------------------------
# MCPServer orchestrator
# ---------------------------------------------------------------------------

class TestMCPServer:
    def test_config_loading(self, tmp_path):
        import yaml

        # Patch backend connection and tool discovery to avoid side effects
        with patch("backends.qdrant_backend.QdrantClient"), \
             patch("backends.qdrant_backend.TextEmbedding"), \
             patch("server.FastMCP"):
            from server import MCPServer

            # Missing file -> empty config
            server = MCPServer(config_path="/nonexistent/config.yaml")
            assert server.config == {}

            # Valid file
            config_file = tmp_path / "config.yaml"
            config_file.write_text(yaml.dump({
                "backend": "qdrant",
                "backend_settings": {"model_name": "test-model"},
            }))
            server = MCPServer(config_path=str(config_file))
            assert server.config["backend"] == "qdrant"
            assert server.config["backend_settings"]["model_name"] == "test-model"

    def test_tool_filtering(self, tmp_path):
        import yaml

        with patch("backends.qdrant_backend.QdrantClient"), \
             patch("backends.qdrant_backend.TextEmbedding"), \
             patch("server.FastMCP"):
            from server import MCPServer

            config_file = tmp_path / "config.yaml"
            config_file.write_text(yaml.dump({
                "enabled_tools": ["search", "list_collections"],
            }))
            server = MCPServer(config_path=str(config_file))
            assert "search" in server.tools
            assert "list_collections" in server.tools
            assert "delete_collection" not in server.tools
            assert "add_documents" not in server.tools
