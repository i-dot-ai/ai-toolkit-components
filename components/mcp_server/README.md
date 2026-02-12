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

## Usage

The MCP server is designed to run alongside a vector database via docker compose.

```bash
# Build and start
docker compose up -d vector_db mcp_server

# Check health
curl http://localhost:8080/health
```

### Docker Compose

```yaml
services:
  vector_db:
    image: vector_db:latest
    ports:
      - "6333:6333"

  mcp_server:
    image: mcp_server:latest
    ports:
      - "8080:8080"
    depends_on:
      - vector_db
    environment:
      - VECTOR_DB_HOST=vector_db
    volumes:
      - ./data/mcp_server:/app/custom
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

# Server settings
server:
  host: "0.0.0.0"
  port: 8080
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
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
