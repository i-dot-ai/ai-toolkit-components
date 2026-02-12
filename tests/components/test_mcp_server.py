"""
Integration tests for the mcp_server component.

Requires Docker to build and run the mcp_server and vector_db containers.
"""

import pytest
import requests

from tests.test_utils import verify_service_health


@pytest.mark.parametrize("component_endpoint", [("mcp_server", "8080")], indirect=True)
def test_health_endpoint(component_endpoint):
    """Test that mcp_server starts and becomes healthy."""
    assert verify_service_health("mcp_server", timeout=120)
    response = requests.get(f"{component_endpoint}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("component_endpoint", [("mcp_server", "8080")], indirect=True)
def test_sse_endpoint_accessible(component_endpoint):
    """Test that the SSE endpoint accepts connections."""
    response = requests.get(f"{component_endpoint}/sse", stream=True, timeout=5)
    assert response.status_code == 200
    response.close()
