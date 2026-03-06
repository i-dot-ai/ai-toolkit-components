# Vector Query

A containerised CLI for querying and managing vector databases directly — useful for testing, ad-hoc exploration, and shell scripting without needing an MCP client.

## Features

- Pluggable backend architecture — drop in a new backend class and it's auto-discovered
- Subcommands for all common operations: search, list, get, add, delete
- Semantic search using FastEmbed embeddings
- Configurable via YAML and environment variables

## Supported Backends

| Backend | Description |
|---------|-------------|
| `qdrant` | Qdrant vector database |

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](../../docs/prerequisites.md) for installation instructions.

## Usage

`vector_query` is designed to run alongside a vector database via docker compose. Start the stack with `docker compose up -d`, then use `docker compose exec` to run query commands against the running container.

```bash
# List all collections
docker compose exec vector_query run list

# Add a document
docker compose exec vector_query run add --collection documents --text "some text to embed"

# Add a document with metadata
docker compose exec vector_query run add \
  --collection documents \
  --text "some text to embed" \
  --metadata '{"source": "manual", "author": "alice"}'

# Search a collection
docker compose exec vector_query run search --query "query text" --collection documents

# Retrieve documents from a collection
docker compose exec vector_query run get --collection documents

# Delete a collection
docker compose exec vector_query run delete --collection documents
```

### Docker Compose

```yaml
services:
  vector_db:
    image: vector_db:latest
    ports:
      - "6333:6333"

  vector_query:
    image: vector_query:latest
    depends_on:
      - vector_db
    environment:
      - VECTOR_DB_HOST=vector_db
    volumes:
      - ./code/vector_query:/app/custom
```

## CLI Reference

```
usage: vector_query [--config PATH] [--json] <command> ...

commands:
  search   Search for documents by semantic similarity
  list     List all collections
  get      Retrieve documents from a collection
  add      Add a document to a collection
  delete   Delete a collection

global options:
  --config PATH   Config file path (default: /app/custom/config/config.yaml)
  --json          Output search results as JSON objects (one per line)
```

### `search`

```
vector_query search --query TEXT [--collection NAME] [--limit N]

  --query             Search query text (required)
  --collection        Collection name (default: documents)
  --limit             Maximum number of results (default: 10)
```

Output (default): `[score=0.92] <text snippet>`
Output (`--json`): one JSON object per line with `id`, `score`, and `payload`.

### `list`

```
vector_query list
```

Prints one collection name per line.

### `get`

```
vector_query get --collection NAME [--limit N] [--offset TOKEN]

  --collection        Collection name (required)
  --limit             Maximum number of documents (default: 10)
  --offset            Pagination offset token from a previous get call
```

Prints each document's payload as a JSON object, one per line. If more pages are available, a `# next_offset: <token>` hint is printed to stderr.

### `add`

```
vector_query add --collection NAME --text TEXT [--metadata JSON]

  --collection        Collection name (required)
  --text              Document text to embed and store (required)
  --metadata          Optional metadata as a JSON string
```

### `delete`

```
vector_query delete --collection NAME

  --collection        Collection name to delete (required)
```

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customisations (defaults copied on first run) |

The custom directory contains:
- `config/` — Configuration files
- `backends/` — Custom backend classes
- `queries/` — Custom query commands

## Configuration

### Config File

Defaults are copied to `/app/custom/config/` on first run. Behavioural settings go here:

```yaml
# Which backend to use (must match a registered backend_type)
backend: qdrant

# Backend-specific settings passed to the backend constructor
backend_settings:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  batch_size: 32
```

### Environment Variables

Connection settings that vary between environments:

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_DB_HOST` | Qdrant server hostname | `localhost` |
| `VECTOR_DB_PORT` | Qdrant server port | `6333` |

## Adding New Queries

Custom queries can be added by placing Python files in the `/app/custom/queries/` volume mount. On first run, the default queries are copied there and can be used as examples. No argparse code is required — CLI flags are generated automatically from the query's `input_schema`.

1. Create a new file in the mounted `queries/` directory (e.g., `count_query.py`)

2. Implement a class inheriting from `BaseQuery` with `query_name`, `description`, `input_schema`, and `execute`:

```python
from backends.base import BaseBackend
from base import BaseQuery


class CountQuery(BaseQuery):
    @property
    def query_name(self) -> str:
        return "count"

    @property
    def description(self) -> str:
        return "Count documents in a collection"

    @property
    def input_schema(self) -> dict:
        return {
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Collection name",
                },
            },
            "required": ["collection"],
        }

    def execute(self, backend: BaseBackend, **kwargs) -> dict:
        result = backend.get_documents(kwargs["collection"], limit=0)
        return {"collection": kwargs["collection"], "count": len(result["documents"])}

    def format_output(self, result, json_output: bool = False) -> None:
        print(f"{result['count']} document(s) in '{result['collection']}'")
```

This automatically registers `count` as a new subcommand:
```bash
docker compose exec vector_query run count --collection documents
```

3. The query is automatically discovered and registered on container restart

## Adding New Backends

Custom backends can be added by placing Python files in the `/app/custom/backends/` volume mount. On first run, the default backends are copied there and can be used as examples.

1. Create a new file in the mounted `backends/` directory (e.g., `weaviate_backend.py`)

2. Implement a class inheriting from `BaseBackend` that implements all required methods and a `backend_type` property:

```python
from base import BaseBackend

class WeaviateBackend(BaseBackend):
    @property
    def backend_type(self) -> str:
        return "weaviate"

    def connect(self) -> None:
        # Establish connection
        ...

    def search(self, collection_name: str, query_text: str, limit: int = 10) -> list[dict]:
        # Return list of dicts with 'id', 'score', 'payload'
        ...

    def list_collections(self) -> list[str]:
        ...

    def get_documents(self, collection_name: str, limit: int = 10, offset: str | None = None) -> dict:
        # Return {'documents': [...], 'next_offset': str | None}
        ...

    def add_documents(self, collection_name: str, documents: list[dict]) -> int:
        # Each document has 'text' and optional 'metadata'
        ...

    def delete_collection(self, collection_name: str) -> bool:
        ...
```

3. Set `backend: weaviate` in your `config/config.yaml`

4. The backend is automatically discovered and registered on container restart
