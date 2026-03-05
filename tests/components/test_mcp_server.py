"""
Integration tests for the mcp_server component.

Requires Docker to build and run the mcp_server and vector_db containers.
"""

import os

import pytest
import requests

from tests.test_utils import verify_service_health


_CUSTOM_MCP_SERVER_PORT = "9080"


@pytest.fixture(scope="module")
def custom_mcp_port():
    """Set MCP_SERVER_PORT so docker compose uses a non-default port."""
    os.environ["MCP_SERVER_PORT"] = _CUSTOM_MCP_SERVER_PORT
    yield
    os.environ.pop("MCP_SERVER_PORT", None)


@pytest.mark.parametrize("component_endpoint", [("mcp_server", "8080")], indirect=True)
class TestMcpServerDefaultPort:

    def test_health_endpoint(self, component_endpoint):
        """Test that mcp_server starts and becomes healthy."""
        assert verify_service_health("mcp_server", timeout=120)
        response = requests.get(f"{component_endpoint}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_sse_endpoint_accessible(self, component_endpoint):
        """Test that the SSE endpoint accepts connections."""
        response = requests.get(f"{component_endpoint}/sse", stream=True, timeout=5)
        assert response.status_code == 200
        response.close()


@pytest.mark.parametrize("component_endpoint", [("mcp_server", _CUSTOM_MCP_SERVER_PORT)], indirect=True)
class TestMcpServerCustomPort:

    def test_responds_on_custom_port(self, custom_mcp_port, component_endpoint):
        """mcp_server /health should be reachable on the custom port."""
        assert verify_service_health("mcp_server", timeout=120)
        response = requests.get(f"{component_endpoint}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_sse_accessible_on_custom_port(self, custom_mcp_port, component_endpoint):
        """mcp_server SSE endpoint should be accessible on the custom port."""
        assert verify_service_health("mcp_server", timeout=120)
        response = requests.get(f"{component_endpoint}/sse", stream=True, timeout=5)
        assert response.status_code == 200
        response.close()
