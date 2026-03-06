"""
Integration tests for the vector_query component.

Requires Docker to build and run containers. Spins up vector_db via the
component_endpoint fixture so vector_query can operate against a real
Qdrant instance.
"""

import subprocess

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VECTOR_DB_PORT = "6333"
QUERY_SERVICE = "vector_query"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("component_service", [QUERY_SERVICE], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("vector_db", VECTOR_DB_PORT)], indirect=True)
class TestVectorQueryContainer:
    """Functional tests that exercise the vector_query CLI against a real
    Qdrant (vector_db) container."""

    def run_query(self, *args, timeout=120):
        """Run the vector_query via exec against the running container.

        Uses the compose network so vector_query can reach vector_db
        by service name.
        """
        cmd = [
            "docker", "compose", "exec", "-T",
            "-e", "VECTOR_DB_HOST=vector_db",
            "-e", f"VECTOR_DB_PORT={VECTOR_DB_PORT}",
            QUERY_SERVICE,
            "run",
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def test_help(self, component_endpoint):
        """Container starts and prints help text with subcommands."""
        result = self.run_query("--help")
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "search" in output
        assert "list" in output
        assert "get" in output
        assert "add" in output
        assert "delete" in output

    def test_list(self, component_endpoint):
        """list command exits 0 and produces valid output."""
        result = self.run_query("list")
        assert result.returncode == 0

    def test_add_and_get(self, component_endpoint):
        """add stores a document; get retrieves it."""
        collection = "test-vq-add-get"
        text = "the quick brown fox jumps over the lazy dog"

        add_result = self.run_query(
            "add", "--collection", collection, "--text", text,
            timeout=180,
        )
        assert add_result.returncode == 0
        assert "stored 1" in add_result.stdout.lower()

        get_result = self.run_query("get", "--collection", collection)
        assert get_result.returncode == 0
        assert text in get_result.stdout

    def test_search(self, component_endpoint):
        """search returns results with scores after a document is added."""
        collection = "test-vq-search"
        text = "vector databases store high-dimensional embeddings"

        add_result = self.run_query(
            "add", "--collection", collection, "--text", text,
            timeout=180,
        )
        assert add_result.returncode == 0

        search_result = self.run_query(
            "search", "--query", "embeddings", "--collection", collection,
            timeout=180,
        )
        assert search_result.returncode == 0
        assert "[score=" in search_result.stdout

    def test_delete(self, component_endpoint):
        """delete removes the collection so it no longer appears in list."""
        collection = "test-vq-delete"

        self.run_query(
            "add", "--collection", collection, "--text", "temporary document",
            timeout=180,
        )

        # Verify collection exists
        list_before = self.run_query("list")
        assert collection in list_before.stdout

        delete_result = self.run_query("delete", "--collection", collection)
        assert delete_result.returncode == 0
        assert collection in delete_result.stdout

        # Verify collection is gone
        list_after = self.run_query("list")
        assert collection not in list_after.stdout
