"""
Integration tests for the vector_db component.

Requires Docker to build and run the vector_db container.
"""

import os
import pytest
import requests

from tests.test_utils import verify_service_health


_CUSTOM_VECTOR_DB_HTTP_PORT = "7333"
_CUSTOM_VECTOR_DB_GRPC_PORT = "7334"


@pytest.fixture(scope="module")
def custom_vector_db_ports():
    """Set VECTOR_DB_HTTP_PORT and VECTOR_DB_GRPC_PORT so docker compose uses non-default ports."""
    os.environ["VECTOR_DB_HTTP_PORT"] = _CUSTOM_VECTOR_DB_HTTP_PORT
    os.environ["VECTOR_DB_GRPC_PORT"] = _CUSTOM_VECTOR_DB_GRPC_PORT
    yield
    os.environ.pop("VECTOR_DB_HTTP_PORT", None)
    os.environ.pop("VECTOR_DB_GRPC_PORT", None)


@pytest.mark.parametrize("component_endpoint", [("vector_db", "6333")], indirect=True)
class TestVectorDbDefaultPort:

    def test_health_endpoint(self, component_endpoint):
        """Test that vector_db starts and becomes healthy."""
        assert verify_service_health("vector_db", timeout=120)

    def test_create_collection(self, component_endpoint):
        """Test we can create a new collection via Qdrant HTTP API."""
        collection_name = "test-collection"
        payload = {
            "vectors": {
                "size": 384,
                "distance": "Cosine"
            }
        }
        response = requests.put(
            f"{component_endpoint}/collections/{collection_name}",
            json=payload,
        )
        assert response.status_code == 200

    def test_get_collections(self, component_endpoint):
        """Test we can retrieve existing collections."""
        response = requests.get(f"{component_endpoint}/collections")
        assert response.status_code == 200
        assert "collections" in response.json()["result"]

    def test_delete_collection(self, component_endpoint):
        """Test we can delete an existing collection."""
        collection_name = "test-collection"
        response = requests.delete(f"{component_endpoint}/collections/{collection_name}")
        assert response.status_code == 200


@pytest.mark.parametrize("component_endpoint", [("vector_db", _CUSTOM_VECTOR_DB_HTTP_PORT)], indirect=True)
class TestVectorDbCustomPort:

    def test_responds_on_custom_http_port(self, custom_vector_db_ports, component_endpoint):
        """vector_db healthz should be reachable on the custom HTTP port."""
        response = requests.get(f"{component_endpoint}/healthz")
        assert response.status_code == 200

    def test_api_usable_on_custom_http_port(self, custom_vector_db_ports, component_endpoint):
        """Collections API should work correctly on the custom HTTP port."""
        response = requests.get(f"{component_endpoint}/collections")
        assert response.status_code == 200
        assert "collections" in response.json()["result"]
