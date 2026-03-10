"""
Integration tests for the data_ingestor component.

Requires Docker to build and run containers. Spins up vector_db via the
component_endpoint fixture so data_ingestor can store embeddings in a real
Qdrant instance.

Both services use the same project so they share a Docker network and
data_ingestor can reach vector_db by service name.
"""

import os
import tempfile

import pytest
import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PROJECT = "test-data_ingestor"
VECTOR_DB_PORT = "6333"
INGESTOR_SERVICE = "data_ingestor"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("component_service", [(INGESTOR_SERVICE, _PROJECT)], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("vector_db", VECTOR_DB_PORT, _PROJECT)], indirect=True)
class TestDataIngestorContainer:
    """Functional tests that exercise the full data_ingestor pipeline
    against a real Qdrant (vector_db) container."""

    def run_ingestor(self, component_service, *args, env_extra=None, timeout=120):
        """Run the data_ingestor via exec against the running container.

        Uses the compose network so data_ingestor can reach vector_db
        by service name.  VECTOR_DB_HOST and VECTOR_DB_PORT are already set
        correctly in the container by docker-compose, so we do not override them.
        """
        return component_service.exec(
            INGESTOR_SERVICE, "run", *args, env=env_extra or {}, timeout=timeout
        )

    def test_help(self, component_endpoint, component_service):
        """Container starts and prints help text."""
        result = self.run_ingestor(component_service, "--help")
        assert result.returncode == 0
        assert "ingest" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_ingest_single_url(self, component_endpoint, component_service):
        """Ingest a single URL and verify the document lands in Qdrant."""
        collection = "test-ingest-single"
        result = self.run_ingestor(
            component_service,
            "-c", collection,
            "http://httpbin.org/html",
        )
        assert result.returncode == 0
        assert "stored 1" in result.stderr.lower() or "stored 1" in result.stdout.lower()

        resp = requests.get(f"{component_endpoint.url}/collections/{collection}")
        assert resp.status_code == 200
        assert resp.json()["result"]["points_count"] == 1

    def test_ingest_multiple_urls(self, component_endpoint, component_service):
        """Ingest multiple URLs into the same collection."""
        collection = "test-ingest-multi"
        urls = [
            "http://httpbin.org/html",
            "http://httpbin.org/forms/post",
        ]
        result = self.run_ingestor(component_service, "-c", collection, *urls)
        assert result.returncode == 0

        resp = requests.get(f"{component_endpoint.url}/collections/{collection}")
        assert resp.status_code == 200
        assert resp.json()["result"]["points_count"] == len(urls)

    def test_ingest_from_file(self, component_endpoint, component_service):
        """Ingest URLs listed in a file."""
        collection = "test-ingest-file"
        container_path = "/tmp/test_urls.txt"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as f:
            f.write("http://httpbin.org/html\n")
            f.write("http://httpbin.org/forms/post\n")
            tmp_path = f.name

        try:
            component_service.cp(tmp_path, f"{INGESTOR_SERVICE}:{container_path}", check=True)
            result = self.run_ingestor(component_service, "-c", collection, "--file", container_path)
            assert result.returncode == 0

            resp = requests.get(f"{component_endpoint.url}/collections/{collection}")
            assert resp.status_code == 200
            assert resp.json()["result"]["points_count"] == 2
        finally:
            os.unlink(tmp_path)

    def test_ingest_idempotent(self, component_endpoint, component_service):
        """Ingesting the same URL twice should upsert, not duplicate."""
        collection = "test-ingest-idempotent"
        url = "http://httpbin.org/html"

        self.run_ingestor(component_service, "-c", collection, url)
        self.run_ingestor(component_service, "-c", collection, url)

        resp = requests.get(f"{component_endpoint.url}/collections/{collection}")
        assert resp.status_code == 200
        assert resp.json()["result"]["points_count"] == 1

    def test_ingest_creates_searchable_embeddings(self, component_endpoint, component_service):
        """Verify stored embeddings are searchable via Qdrant scroll API."""
        collection = "test-ingest-search"
        self.run_ingestor(component_service, "-c", collection, "http://httpbin.org/html")

        resp = requests.post(
            f"{component_endpoint.url}/collections/{collection}/points/scroll",
            json={"limit": 10, "with_payload": True, "with_vector": False},
        )
        assert resp.status_code == 200
        points = resp.json()["result"]["points"]
        assert len(points) == 1

        payload = points[0]["payload"]
        assert payload["source"] == "http://httpbin.org/html"
        assert payload["source_type"] == "html"
        assert payload["title"]
        assert payload["content"]

    def test_ingest_bad_url_exits_cleanly(self, component_endpoint, component_service):
        """Ingestor should handle unreachable URLs gracefully."""
        collection = "test-ingest-bad"
        result = self.run_ingestor(
            component_service,
            "-c", collection,
            "https://this-domain-does-not-exist-xyz.com",
        )
        assert result.returncode == 0
        assert "no documents" in result.stderr.lower() or "stored 0" in result.stderr.lower()

    def test_ingest_unsupported_source_type_warns(self, component_endpoint, component_service):
        """Ingestor should warn when no parser exists for a source type."""
        result = self.run_ingestor(
            component_service,
            "-c", "test-unsupported",
            "/tmp/test.unsupported",
        )
        assert result.returncode == 0
        assert "no parser for type" in result.stderr.lower()
        assert "no documents" in result.stderr.lower()
