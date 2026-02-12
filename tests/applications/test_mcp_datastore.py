import subprocess

import pytest

from tests.test_utils import verify_service_health
from tests.test_utils import get_application_services


APP_NAME = "mcp_datastore"


@pytest.mark.parametrize("application_endpoint", [APP_NAME], indirect=True)
class TestMcpDatastore:
    """Integration tests for the mcp_datastore application."""

    def test_service_health(self, application_endpoint):
        """Test that long-running services start and become healthy."""
        # data_ingestor is a run-once service, only check vector_db and mcp_server
        assert verify_service_health("vector_db"), "vector_db is unhealthy"
        assert verify_service_health("mcp_server"), "mcp_server is unhealthy"

    def test_mcp_server_health(self, application_endpoint):
        """Test that mcp_server health endpoint responds within the application stack."""
        import requests
        response = requests.get("http://localhost:8080/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_custom_tool_is_discovered_and_callable(self, application_endpoint, custom_tool_code):
        """Test that a custom tool added to code/ is discovered and callable."""
        compose_file = application_endpoint / "docker-compose.yaml"

        # Add a custom ping tool
        tools_dir = application_endpoint / "code" / "mcp_server" / "tools"
        assert tools_dir.exists(), "Entrypoint should have created tools directory"
        (tools_dir / "ping_tool.py").write_text(custom_tool_code)

        # Restart mcp_server so it re-imports tools
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "restart", "mcp_server"],
            cwd=application_endpoint,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Failed to restart mcp_server: {result.stderr}"

        # Wait for mcp_server to become healthy again
        assert verify_service_health("mcp_server"), "mcp_server is unhealthy after restart"

        # Check container logs for tool registration
        logs_result = subprocess.run(
            ["docker", "logs", "mcp_server"],
            capture_output=True,
            text=True,
        )
        logs = logs_result.stdout + logs_result.stderr

        assert "Enabled tool: ping" in logs, \
            f"Custom tool not enabled. Logs:\n{logs}"
        assert "Tool discovery complete: 6 enabled" in logs, \
            f"Expected 6 tools after adding ping. Logs:\n{logs}"

    def test_custom_parser_is_discovered_and_used(self, application_endpoint, custom_parser_code):
        """Test that a custom parser added to code/ is discovered and used."""
        compose_file = application_endpoint / "docker-compose.yaml"

        # Add a custom parser for .test files
        parser_dir = application_endpoint / "code" / "data_ingestor" / "parsers"
        assert parser_dir.exists(), "Entrypoint should have created parsers directory"
        (parser_dir / "test_parser.py").write_text(custom_parser_code)

        # Create a test file to ingest
        test_file = "/app/custom/sample.test"
        (parser_dir.parent / "sample.test").write_text("This is test content for the custom parser.")

        # Run data_ingestor with the test file
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "run", "--rm",
             "data_ingestor", test_file],
            cwd=application_endpoint,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr

        # Check that the custom parser was used
        assert "Creating parser: TestParser" in output, \
            f"Custom parser not loaded. Output:\n{output}"

        # Check that auto-detection selected the correct parser type
        assert "Parsing (test):" in output, \
            f"Parser auto-detection failed. Output:\n{output}"

        # Check that ingestion succeeded
        assert "Ingested 1 document(s)" in output, \
            f"Ingestion failed. Output:\n{output}"
