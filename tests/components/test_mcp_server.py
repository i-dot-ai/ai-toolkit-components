"""
Integration tests for the mcp_server component.

Requires Docker to build and run the mcp_server and vector_db containers.
"""

import pytest
import requests


_PROJECT = "test-mcp_server"
_PORT_VARS = ["MCP_SERVER_PORT", "VECTOR_DB_HTTP_PORT", "VECTOR_DB_GRPC_PORT"]


@pytest.mark.parametrize("port_env_map", [_PORT_VARS], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("mcp_server", _PROJECT)], indirect=True)
class TestMcpServerDefaultPort:

    def test_health_endpoint(self, component_endpoint):
        """Test that mcp_server starts and becomes healthy."""
        assert component_endpoint.verify_health("mcp_server", timeout=120)
        response = requests.get(f"{component_endpoint.url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_sse_endpoint_accessible(self, component_endpoint):
        """Test that the SSE endpoint accepts connections."""
        response = requests.get(f"{component_endpoint.url}/sse", stream=True, timeout=5)
        assert response.status_code == 200
        response.close()


@pytest.mark.parametrize("port_env_map", [_PORT_VARS], indirect=True)
@pytest.mark.parametrize("component_endpoint", [("mcp_server", _PROJECT)], indirect=True)
class TestMcpServerCustomPort:

    def test_responds_on_custom_port(self, component_endpoint):
        """mcp_server /health should be reachable on a non-default port."""
        assert component_endpoint.verify_health("mcp_server", timeout=120)
        response = requests.get(f"{component_endpoint.url}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_sse_accessible_on_custom_port(self, component_endpoint):
        """mcp_server SSE endpoint should be accessible on a non-default port."""
        assert component_endpoint.verify_health("mcp_server", timeout=120)
        response = requests.get(f"{component_endpoint.url}/sse", stream=True, timeout=5)
        assert response.status_code == 200
        response.close()
