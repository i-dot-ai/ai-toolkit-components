# MCP Server

A containerised MCP (Model Context Protocol) server that exposes vector database operations as tools for AI agents.

## Features

- Pluggable backend architecture - support for multiple vector databases
- Pluggable tool architecture - easily extend with new operations
- Auto-discovery of backend and tool classes
- All tools automatically exposed via MCP protocol over SSE transport
- Configurable via YAML and environment variables

## Supported Backends

| Backend | Description |
|---------|-------------|
| `qdrant` | Qdrant vector database |

## Available Tools

| Tool | Description |
|------|-------------|
| `search` | Semantic similarity search over a collection |
| `list_collections` | List all available collections |
| `get_documents` | Retrieve documents with pagination |
| `delete_collection` | Delete an entire collection |
| `add_documents` | Add documents with automatic embedding |

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](../../docs/prerequisites.md) for installation instructions.

## Usage

The MCP server is designed to run alongside a vector database via docker compose.

### Using the Published Image

To run the service using the published docker image, add the below snippet to your docker compose file:

```yaml
services:
  vector_db:
    image: ghcr.io/i-dot-ai/ai-toolkit-vector-db:latest
    ports:
      - "${VECTOR_DB_HTTP_PORT:-6333}:${VECTOR_DB_HTTP_PORT:-6333}"
    environment:
      - VECTOR_DB_BIND_HOST=${VECTOR_DB_BIND_HOST:-0.0.0.0}
      - VECTOR_DB_HTTP_PORT=${VECTOR_DB_HTTP_PORT:-6333}

  mcp_server:
    image: ghcr.io/i-dot-ai/ai-toolkit-mcp-server:latest
    ports:
      - "${MCP_SERVER_PORT:-8080}:${MCP_SERVER_PORT:-8080}"
    depends_on:
      - vector_db
    environment:
      - MCP_SERVER_HOST=${MCP_SERVER_HOST:-0.0.0.0}
      - MCP_SERVER_PORT=${MCP_SERVER_PORT:-8080}
      - VECTOR_DB_HOST=vector_db
      - VECTOR_DB_PORT=${VECTOR_DB_HTTP_PORT:-6333}
    volumes:
      - ./data/mcp_server:/app/custom
```

Note that this includes the `vector_db` component — if you wish to run alongside an alternative database you can replace that section.

The services can then be run via:

```bash
docker compose up -d vector_db mcp_server
```

Or to run just the `mcp_server`:

```bash
docker compose up -d mcp_server
```

### Building from Source

To build and run from source, add the below snippet to your docker compose file:

```yaml
services:
  vector_db:
    build:
      context: .
      dockerfile: components/vector_db/Dockerfile
    ports:
      - "${VECTOR_DB_HTTP_PORT:-6333}:${VECTOR_DB_HTTP_PORT:-6333}"
    environment:
      - VECTOR_DB_BIND_HOST=${VECTOR_DB_BIND_HOST:-0.0.0.0}
      - VECTOR_DB_HTTP_PORT=${VECTOR_DB_HTTP_PORT:-6333}

  mcp_server:
    build:
      context: .
      dockerfile: components/mcp_server/Dockerfile
    ports:
      - "${MCP_SERVER_PORT:-8080}:${MCP_SERVER_PORT:-8080}"
    depends_on:
      - vector_db
    environment:
      - MCP_SERVER_HOST=${MCP_SERVER_HOST:-0.0.0.0}
      - MCP_SERVER_PORT=${MCP_SERVER_PORT:-8080}
      - VECTOR_DB_HOST=vector_db
      - VECTOR_DB_PORT=${VECTOR_DB_HTTP_PORT:-6333}
    volumes:
      - ./data/mcp_server:/app/custom
```

Note that this includes the `vector_db` component — if you wish to run alongside an alternative database you can replace that section.

The services can then be built and run via:

```bash
docker compose build vector_db mcp_server
docker compose up -d vector_db mcp_server
```

Or to build and run just the `mcp_server`:

```bash
docker compose build mcp_server
docker compose up -d mcp_server
```

```bash
# Check health
curl http://localhost:8080/health
```

### Connecting an MCP Client

The server exposes SSE transport at:
- **SSE endpoint:** `http://localhost:8080/sse`
- **Messages endpoint:** `http://localhost:8080/messages/`

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customisations (defaults copied on first run) |

The custom directory contains:
- `config/` - Configuration files
- `backends/` - Custom backend classes
- `tools/` - Custom tool classes

## Configuration

### Config File

Defaults are copied to `/app/custom/config/` on first run.

```yaml
# Backend type
backend: qdrant

# Backend-specific settings
backend_settings:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  batch_size: 32

# Tools to enable (omit to enable all)
# enabled_tools:
#   - search
#   - list_collections
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_HOST` | Host address the server binds to | `0.0.0.0` |
| `MCP_SERVER_PORT` | MCP server port | `8080` |
| `VECTOR_DB_HOST` | Vector database hostname | `localhost` |
| `VECTOR_DB_PORT` | Vector database port | `6333` |

## Adding Custom Tools

Custom tools can be added by placing Python files in the `/app/custom/tools/` volume mount.

1. Create a new file (e.g., `count_tool.py`)

2. Implement a class inheriting from `BaseTool`:

```python
from base import BaseTool

class CountTool(BaseTool):
    @property
    def tool_name(self) -> str:
        return "count_documents"

    @property
    def description(self) -> str:
        return "Count documents in a collection"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "collection_name": {
                    "type": "string",
                    "description": "Name of the collection",
                },
            },
            "required": ["collection_name"],
        }

    def execute(self, backend, **kwargs):
        result = backend.get_documents(kwargs["collection_name"], limit=0)
        return {"count": len(result["documents"])}
```

3. The tool is automatically discovered and registered on container restart

## Adding Custom Backends

Custom backends can be added by placing Python files in the `/app/custom/backends/` volume mount.

1. Create a new file (e.g., `pinecone_backend.py`)

2. Implement a class inheriting from `BaseBackend`:

```python
from base import BaseBackend

class PineconeBackend(BaseBackend):
    @property
    def backend_type(self) -> str:
        return "pinecone"

    def connect(self):
        # Establish connection
        ...

    def search(self, collection_name, query_text, limit=10):
        # Implement search
        ...

    def list_collections(self):
        # List collections
        ...

    def get_documents(self, collection_name, limit=10, offset=None):
        # Retrieve documents
        ...

    def delete_collection(self, collection_name):
        # Delete collection
        ...

    def add_documents(self, collection_name, documents):
        # Add documents
        ...
```

3. Update `config.yaml` to use the new backend:
```yaml
backend: pinecone
```

4. The backend is automatically discovered and registered on container restart
