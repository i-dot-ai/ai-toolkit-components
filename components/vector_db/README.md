# Vector DB

A containerised Qdrant vector database with plugin support for automatic collection setup and configuration management.

## Features

- Based on official Qdrant image
- Automatic plugin execution on startup
- Default configuration and plugin copying to mounted volumes
- Health check endpoint at `/healthz`
- Customisable collection setup via Python plugins

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 6333 | HTTP | REST API |
| 6334 | gRPC | gRPC API |

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](../../docs/prerequisites.md) for installation instructions.

## Usage

### Using the Published Image

To run the service using the published docker image, add the below snippet to your docker compose file:

```yaml
services:
  vector_db:
    image: ghcr.io/i-dot-ai/ai-toolkit-vector-db:latest
    ports:
      - "${VECTOR_DB_HTTP_PORT:-6333}:${VECTOR_DB_HTTP_PORT:-6333}"
      - "${VECTOR_DB_GRPC_PORT:-6334}:${VECTOR_DB_GRPC_PORT:-6334}"
    environment:
      - VECTOR_DB_BIND_HOST=${VECTOR_DB_BIND_HOST:-0.0.0.0}
      - VECTOR_DB_HTTP_PORT=${VECTOR_DB_HTTP_PORT:-6333}
      - VECTOR_DB_GRPC_PORT=${VECTOR_DB_GRPC_PORT:-6334}
    volumes:
      - ./data/vector_db:/app/custom
```

Then start the service:

```bash
docker compose up -d vector_db
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
      - "${VECTOR_DB_GRPC_PORT:-6334}:${VECTOR_DB_GRPC_PORT:-6334}"
    environment:
      - VECTOR_DB_BIND_HOST=${VECTOR_DB_BIND_HOST:-0.0.0.0}
      - VECTOR_DB_HTTP_PORT=${VECTOR_DB_HTTP_PORT:-6333}
      - VECTOR_DB_GRPC_PORT=${VECTOR_DB_GRPC_PORT:-6334}
    volumes:
      - ./data/vector_db:/app/custom
```

Then build and start the service:

```bash
docker compose build vector_db
docker compose up -d vector_db
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_DB_BIND_HOST` | Host address the database binds to | `0.0.0.0` |
| `VECTOR_DB_HTTP_PORT` | HTTP REST API port | `6333` |
| `VECTOR_DB_GRPC_PORT` | gRPC API port | `6334` |

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customizations (defaults copied on first run) |

The custom directory contains:
- `config/` - Configuration files
- `plugins/` - Python plugins executed on startup

## Plugins

Python scripts placed in `/app/custom/plugins/` are automatically executed after Qdrant starts. This enables custom collection setup, index configuration, and other initialisation tasks.

### Writing Custom Plugins

An `example_plugin.py` is included as a starting point.

Create a Python file in the plugins directory:

```python
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

def main():
    client = QdrantClient(
        host=os.getenv("VECTOR_DB_HOST", "localhost"),
        port=int(os.getenv("VECTOR_DB_PORT", 6333))
    )

    # Create custom collection
    client.create_collection(
        collection_name="my_collection",
        vectors_config=models.VectorParams(
            size=384,
            distance=models.Distance.COSINE
        )
    )

if __name__ == "__main__":
    main()
```

## API Examples

```bash
# Health check
curl http://localhost:6333/healthz

# List collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/documents

# Create a collection
curl -X PUT http://localhost:6333/collections/my_collection \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'

# Delete a collection
curl -X DELETE http://localhost:6333/collections/my_collection
```
