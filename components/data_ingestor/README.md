# Data Ingestor

A containerized service for ingesting content from various sources, converting it to a standardized format, and embedding it into vector databases.

## Features

- Pluggable parser architecture - easily extend to support new content types
- Pluggable embedder architecture - support for multiple vector databases
- Auto-discovery of parser and embedder classes
- Standardized document format for embedding pipelines
- Configurable via YAML
- Batch processing support

## Supported Source Types

| Type | Description |
|------|-------------|
| `html` | Web pages fetched via URL |

## Supported Vector Stores

| Store | Description |
|-------|-------------|
| `qdrant` | Qdrant vector database |

## Document Format

All parsers produce documents in the following structure:

```json
{
  "source": "https://example.com/page",
  "title": "Page Title",
  "content": "Extracted text content...",
  "metadata": {
    "domain": "example.com",
    "path": "/page",
    "description": "Meta description if available"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "source_type": "html"
}
```

## Usage

### Ingest and Output to JSON

```bash
# Build the image
docker build -t data-ingestor .

# Ingest a single URL to JSON
docker run -v $(pwd)/output:/app/output data-ingestor \
  --source https://example.com

# Ingest multiple URLs from a file
docker run -v $(pwd)/urls.txt:/app/urls.txt -v $(pwd)/output:/app/output \
  data-ingestor --sources-file /app/urls.txt
```

### Ingest and Embed into Vector Database

```bash
# Ingest and embed into Qdrant (requires Qdrant to be running)
docker run --network host data-ingestor \
  --source https://example.com \
  --embed \
  --store qdrant \
  --collection my_documents

# With custom Qdrant host via config
docker run -v $(pwd)/config.yaml:/app/config/config.yaml data-ingestor \
  --source https://example.com \
  --embed
```

### Docker Compose with Vector DB

```yaml
services:
  vector_db:
    image: vector_db:latest
    ports:
      - "6333:6333"

  data-ingestor:
    image: data-ingestor:latest
    depends_on:
      - vector_db
    volumes:
      - ./config.yaml:/app/config/config.yaml
      - ./urls.txt:/app/urls.txt
    command: ["--sources-file", "/app/urls.txt", "--embed", "--collection", "documents"]
```

## Configuration

Configuration is split between config file (behavioral settings) and environment variables (connection settings).

### Config File

Mount a custom config directory to `/app/config/`. Behavioral settings go here:

```yaml
# General settings
request_delay: 1.0

# Parser settings
html:
  user_agent: "MyBot/1.0"
  timeout: 30

# Embedder settings (behavioral only - connection via env vars)
qdrant:
  model_name: "all-MiniLM-L6-v2"
  batch_size: 32
```

### Environment Variables

Connection settings that vary between environments:

| Variable | Description | Default |
|----------|-------------|---------|
| `QDRANT_HOST` | Qdrant server hostname | `localhost` |
| `QDRANT_PORT` | Qdrant server port | `6333` |

## CLI Options

| Option | Description |
|--------|-------------|
| `--source` | Single source to ingest (URL, file path, etc.) |
| `--sources-file` | File containing sources, one per line |
| `--type`, `-t` | Source type (default: `html`) |
| `--output`, `-o` | Output JSON file path (when not embedding) |
| `--config` | Config file path (default: `/app/config/config.yaml`) |
| `--embed` | Embed documents into vector database |
| `--store`, `-s` | Vector store type (default: `qdrant`) |
| `--collection`, `-c` | Collection name for vector store (default: `documents`) |

## Adding New Parsers

1. Create a new file in `src/parsers/` (e.g., `pdf_parser.py`)

2. Implement a class inheriting from `BaseParser`:

```python
from .base import BaseParser, ParsedDocument

class PDFParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "pdf"

    def parse(self, content: bytes, source: str) -> ParsedDocument:
        text = extract_pdf_text(content)

        return ParsedDocument(
            source=source,
            title="Extracted title",
            content=text,
            metadata={"pages": page_count},
            timestamp=self._current_timestamp(),
            source_type=self.source_type
        )

    def fetch(self, source: str) -> bytes:
        with open(source, "rb") as f:
            return f.read()
```

3. The parser is automatically discovered and registered on import

## Adding New Embedders

1. Create a new file in `src/embedders/` (e.g., `pinecone_embedder.py`)

2. Implement a class inheriting from `BaseEmbedder`:

```python
from .base import BaseEmbedder
from parsers.base import ParsedDocument

class PineconeEmbedder(BaseEmbedder):
    def __init__(self, api_key: str = "", environment: str = ""):
        self.api_key = api_key
        self.environment = environment

    @property
    def store_type(self) -> str:
        return "pinecone"

    def embed(self, text: str) -> list[float]:
        # Generate embedding vector
        return embedding_vector

    def store(self, documents: list[ParsedDocument], collection_name: str) -> int:
        # Store documents in Pinecone
        return len(documents)
```

3. The embedder is automatically discovered and registered on import
