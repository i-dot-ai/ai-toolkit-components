"""
Integration tests for the vector_query component.

Requires Docker to build and run containers. Spins up vector_db via the
component_endpoint fixture so vector_query can operate against a real
Qdrant instance.

Both services use the same project so they share a Docker network and
vector_query can reach vector_db by service name.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT = "test-vector_query"
QUERY_SERVICE = "vector_query"
_PORT_VARS = ["VECTOR_DB_HTTP_PORT", "VECTOR_DB_GRPC_PORT"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("port_env_map", [_PORT_VARS], indirect=True)
@pytest.mark.parametrize("component_service", [(QUERY_SERVICE, _PROJECT)], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("vector_db", _PROJECT)], indirect=True)
class TestVectorQueryContainer:
    """Functional tests that exercise the vector_query CLI against a real
    Qdrant (vector_db) container."""

    def run_query(self, component_service, *args, timeout=120):
        """Run the vector_query via exec against the running container.

        Both services share a project network, so vector_db is reachable
        by its service name.  VECTOR_DB_HOST and VECTOR_DB_PORT are already set
        correctly in the container by docker-compose, so we do not override them.
        """
        return component_service.exec(QUERY_SERVICE, "run", *args, timeout=timeout)

    def test_help(self, component_endpoint, component_service):
        """Container starts and prints help text with subcommands."""
        result = self.run_query(component_service, "--help")
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "search" in output
        assert "list" in output
        assert "get" in output
        assert "add" in output
        assert "delete" in output

    def test_list(self, component_endpoint, component_service):
        """list command exits 0 and produces valid output."""
        result = self.run_query(component_service, "list")
        assert result.returncode == 0

    def test_add_and_get(self, component_endpoint, component_service):
        """add stores a document; get retrieves it."""
        collection = "test-vq-add-get"
        text = "the quick brown fox jumps over the lazy dog"

        add_result = self.run_query(
            component_service,
            "add", "--collection", collection, "--text", text,
            timeout=180,
        )
        assert add_result.returncode == 0
        assert "stored 1" in add_result.stdout.lower()

        get_result = self.run_query(component_service, "get", "--collection", collection)
        assert get_result.returncode == 0
        assert text in get_result.stdout

    def test_search(self, component_endpoint, component_service):
        """search returns results with scores after a document is added."""
        collection = "test-vq-search"
        text = "vector databases store high-dimensional embeddings"

        add_result = self.run_query(
            component_service,
            "add", "--collection", collection, "--text", text,
            timeout=180,
        )
        assert add_result.returncode == 0

        search_result = self.run_query(
            component_service,
            "search", "--query", "embeddings", "--collection", collection,
            timeout=180,
        )
        assert search_result.returncode == 0
        assert "[score=" in search_result.stdout

    def test_delete(self, component_endpoint, component_service):
        """delete removes the collection so it no longer appears in list."""
        collection = "test-vq-delete"

        self.run_query(
            component_service,
            "add", "--collection", collection, "--text", "temporary document",
            timeout=180,
        )

        list_before = self.run_query(component_service, "list")
        assert collection in list_before.stdout

        delete_result = self.run_query(component_service, "delete", "--collection", collection)
        assert delete_result.returncode == 0
        assert collection in delete_result.stdout

        list_after = self.run_query(component_service, "list")
        assert collection not in list_after.stdout
