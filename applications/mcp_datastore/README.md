# MCP Datastore

A vector database application for ingesting, storing, and querying document embeddings. Combines the `vector_db`, `data_ingestor`, and `mcp_server` components to provide a complete content ingestion, retrieval, and AI agent access pipeline.

```
┌──────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  data_ingestor   │────▶│    vector_db    │◀────│   mcp_server    │
│                  │     │    (Qdrant)     │     │                 │
│  - Custom parsers│     │                 │     │  - MCP protocol │
│  - Embedder      │     │  - Collections  │     │  - SSE transport│
└──────────────────┘     │  - Plugins      │     │  - Custom tools │
                         └─────────────────┘     └─────────────────┘
                               │                        │
                         ┌─────┴─────┐           ┌──────┴────┐
                         │  :6333    │           │  :8080    │
                         │  :6334    │           └───────────┘
                         └───────────┘
```

## Components

| Component | Description |
|-----------|-------------|
| [vector_db](/components/vector_db/README.md) | Qdrant vector database with plugin support |
| [data_ingestor](/components/data_ingestor/README.md) | Content ingestion and embedding service |
| [mcp_server](/components/mcp_server/README.md) | MCP server exposing vector DB tools for AI agents |

## Features

- Automatic collection setup via vector_db plugin
- HTML content parsing
- Vector embedding generation using sentence-transformers
- Configurable parsers and embedders via mounted volumes
- MCP protocol server for AI agent tool access
- Pluggable custom tools and backends for the MCP server

## Usage

Copy [`docker-compose.yaml`](docker-compose.yaml) into the directory where you wish to run the application, then run all commands from that directory.

### Start the Vector Database

```bash
docker compose up -d vector_db
```

### Ingest Content

Use `docker compose run` to execute the data ingestor within the compose network:

```bash
# Ingest a single URL
docker compose run data_ingestor https://example.com

# Ingest multiple URLs
docker compose run data_ingestor \
  https://example.com \
  https://example.com/page2

# Ingest from a file - maybe something about this command would read the following file root/url.txt
docker compose run -v $(pwd)/urls.txt:/app/urls.txt \
  data_ingestor -f /app/urls.txt

# Specify a collection name
docker compose run data_ingestor -c my_collection https://example.com
```

### Ingest Local Files

To ingest local files, place them in an `input/` directory within your working directory. The data_ingestor container mounts this directory automatically:

```bash
# Create the input directory and add files
mkdir -p input
cp my_document.html input/

# Ingest a local file
docker compose run data_ingestor input/my_document.html

# Ingest multiple local files
docker compose run data_ingestor input/doc1.html input/doc2.html
```

**Note:** Only files within the `input/` directory are accessible to the data_ingestor container.

### Query the Database

```bash
# List collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/documents

# Health check
curl http://localhost:6333/healthz
```

### Use the MCP Server

Start the MCP server alongside the vector database:

```bash
docker compose up -d vector_db mcp_server
```

Check it is healthy:

```bash
curl http://localhost:8080/health
```

#### Connecting an MCP Client

The server uses SSE transport. Point your MCP client at:

- **SSE endpoint:** `http://localhost:8080/sse`
- **Messages endpoint:** `http://localhost:8080/messages/`

For example, to add it to Claude Code:

```bash
claude mcp add mcp_datastore --transport sse http://localhost:8080/sse
```

All tools are enabled by default. To restrict which tools are exposed, set `enabled_tools` in `code/mcp_server/config/config.yaml`:

```yaml
enabled_tools:
  - search
  - list_collections
  - get_documents
```

### Stop the Application

```bash
docker compose down
```

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| 6333 | HTTP | Qdrant REST API |
| 6334 | gRPC | Qdrant gRPC API |
| 8080 | HTTP | MCP server (SSE transport) |

## Configuration

Configuration files are mounted from the `code/` directory:

| Path | Description |
|------|-------------|
| `code/vector_db/config/` | Vector database configuration |
| `code/vector_db/plugins/` | Startup plugins (e.g., collection setup) |
| `code/data_ingestor/config/` | Ingestor configuration |
| `code/data_ingestor/parsers/` | Custom parser classes |
| `code/data_ingestor/embedders/` | Custom embedder classes |
| `code/mcp_server/config/` | MCP server configuration |
| `code/mcp_server/tools/` | Custom MCP tool classes |
| `code/mcp_server/backends/` | Custom MCP backend classes |

### Default Configuration

The data ingestor is configured with:

- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional vectors)
- **Collection**: `documents` (created automatically by the setup plugin)
- **Distance metric**: Cosine similarity

### Customisation

Each component writes default code into its `code/` subdirectory on first run. Edit those files or add new ones — changes take effect on the next container restart.

1. Edit `code/data_ingestor/config/config.yaml` to change the embedding model, batch size, or parser settings
2. Edit `code/mcp_server/config/config.yaml` to change the backend, server port, or restrict which tools are exposed via `enabled_tools`
3. Add custom parsers to `code/data_ingestor/parsers/` — subclass `BaseParser` and implement `source_type`, `fetch`, and `parse`
4. Add custom embedders to `code/data_ingestor/embedders/` — subclass `BaseEmbedder` and implement `store_type` and `store`
5. Add custom MCP tools to `code/mcp_server/tools/` — subclass `BaseTool` and implement `tool_name`, `description`, `input_schema`, and `execute`
6. Add custom MCP backends to `code/mcp_server/backends/` — subclass `BaseBackend` and implement the required database operations
7. Add startup plugins to `code/vector_db/plugins/` for collection setup and index configuration
8. Restart the relevant services for changes to take effect

See individual component READMEs for detailed examples of each extension point.

## Resource Limits

| Service | Memory Limit | CPU Limit |
|---------|--------------|-----------|
| vector_db | 4GB | 2 cores |
| data_ingestor | 2GB | 1 core |
| mcp_server | 2GB | 1 core |
