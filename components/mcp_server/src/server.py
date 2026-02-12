"""
MCP Server - exposes vector database operations as MCP tools.

Discovers backend and tool plugins, then serves them over the MCP
protocol using FastMCP with SSE transport.
"""

import argparse
import logging
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from backends import available_backends, get_backend_class
from tools import available_tools, get_tool_class

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "/app/custom/config/config.yaml"


class MCPServer:
    """
    Orchestrator that wires up a vector database backend with
    auto-discovered tools and serves them as an MCP server over SSE.
    """

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config = self._load_config(config_path)
        self.backend = self._init_backend()
        self.tools = self._discover_tools()

        server_config = self.config.get("server", {})
        self.mcp = FastMCP(
            "mcp-server",
            host=server_config.get("host", "0.0.0.0"),
            port=server_config.get("port", 8080),
        )

        self._register_health()
        self._register_tools()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from a YAML file."""
        path = Path(config_path)
        if not path.exists():
            logger.warning(
                f"Config file not found at {config_path}, using defaults"
            )
            return {}

        with open(path) as f:
            config = yaml.safe_load(f) or {}

        logger.info(f"Loaded config from {config_path}")
        return config

    def _init_backend(self):
        """Instantiate and connect the configured backend."""
        backend_type = self.config.get("backend", "qdrant")
        backend_settings = self.config.get("backend_settings", {})

        logger.info(
            f"Initialising backend: {backend_type} "
            f"(available: {available_backends})"
        )

        cls = get_backend_class(backend_type)
        backend = cls(**backend_settings)
        backend.connect()
        return backend

    def _discover_tools(self) -> dict:
        """Discover and optionally filter tool plugins."""
        enabled = self.config.get("enabled_tools")
        tool_instances = {}

        for name in available_tools:
            if enabled is not None and name not in enabled:
                logger.info(f"Skipping disabled tool: {name}")
                continue
            cls = get_tool_class(name)
            tool_instances[name] = cls()
            logger.info(f"Enabled tool: {name}")

        logger.info(
            f"Tool discovery complete: {len(tool_instances)} enabled "
            f"({list(tool_instances.keys())})"
        )
        return tool_instances

    def _register_health(self) -> None:
        """Register a /health endpoint for container health checks."""

        @self.mcp.custom_route("/health", methods=["GET"])
        async def health(request: Request) -> JSONResponse:
            return JSONResponse({"status": "ok"})

    def _register_tools(self) -> None:
        """Register discovered tools as MCP tools."""
        for name, tool in self.tools.items():
            self.mcp.tool(name=tool.tool_name, description=tool.description)(
                tool.as_handler(self.backend)
            )

    def run(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        """Start the MCP server with SSE transport."""
        server_config = self.config.get("server", {})
        self.mcp.settings.host = server_config.get("host", host)
        self.mcp.settings.port = server_config.get("port", port)

        logger.info(
            f"Starting MCP server on "
            f"{self.mcp.settings.host}:{self.mcp.settings.port}"
        )
        self.mcp.run(transport="sse")


def main():
    parser = argparse.ArgumentParser(
        description="MCP Server for vector database operations"
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_PATH,
        help="Path to config file",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = MCPServer(config_path=args.config)
    server.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
