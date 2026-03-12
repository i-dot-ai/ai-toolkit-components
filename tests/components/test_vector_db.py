"""
Integration tests for the vector_db component.

Requires Docker to build and run the vector_db container.
"""

import pytest
import requests


_PROJECT = "test-vector_db"
_PORT_VARS = ["VECTOR_DB_HTTP_PORT", "VECTOR_DB_GRPC_PORT"]


@pytest.mark.parametrize("port_env_map", [_PORT_VARS], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("vector_db", _PROJECT)], indirect=True)
class TestVectorDbDefaultPort:

    def test_health_endpoint(self, component_endpoint):
        """Test that vector_db starts and becomes healthy."""
        assert component_endpoint.verify_health("vector_db", timeout=120)

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
            f"{component_endpoint.url}/collections/{collection_name}",
            json=payload,
        )
        assert response.status_code == 200

    def test_get_collections(self, component_endpoint):
        """Test we can retrieve existing collections."""
        response = requests.get(f"{component_endpoint.url}/collections")
        assert response.status_code == 200
        assert "collections" in response.json()["result"]

    def test_delete_collection(self, component_endpoint):
        """Test we can delete an existing collection."""
        collection_name = "test-collection"
        response = requests.delete(f"{component_endpoint.url}/collections/{collection_name}")
        assert response.status_code == 200


@pytest.mark.parametrize("port_env_map", [_PORT_VARS], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("vector_db", _PROJECT)], indirect=True)
class TestVectorDbCustomPort:

    def test_responds_on_custom_http_port(self, component_endpoint):
        """vector_db healthz should be reachable on a non-default HTTP port."""
        response = requests.get(f"{component_endpoint.url}/healthz")
        assert response.status_code == 200

    def test_api_usable_on_custom_http_port(self, component_endpoint):
        """Collections API should work correctly on a non-default HTTP port."""
        response = requests.get(f"{component_endpoint.url}/collections")
        assert response.status_code == 200
        assert "collections" in response.json()["result"]
