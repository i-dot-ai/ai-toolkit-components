# Data Ingestor

A containerised service for ingesting content from various sources and embedding it into vector databases.

## Features

- Pluggable parser architecture - easily extend to support new content types
- Pluggable embedder architecture - support for multiple vector databases
- Pluggable chunker architecture - split large documents for better retrieval
- Auto-discovery of parser, embedder, and chunker classes
- Simple CLI - just pass URLs as arguments
- Configurable via YAML and environment variables

## Supported Source Types

| Type | Description |
|------|-------------|
| `html` | Web pages fetched via URL |
| `unstructured` | Multi-format parser (PDF, DOCX, XLSX, PPTX, etc.) - requires optional dependencies |

### Multi-Format Parsing (Optional)

When built with `INSTALL_UNSTRUCTURED=true` (the default), the data ingestor can parse many document formats automatically:

| Format | Extensions |
|--------|------------|
| PDF | `.pdf` |
| Word | `.docx`, `.doc` |
| Excel | `.xlsx`, `.xls` |
| PowerPoint | `.pptx`, `.ppt` |
| Text | `.txt`, `.md`, `.csv` |
| Email | `.msg`, `.eml` |
| Other | `.rtf`, `.odt`, `.epub`, `.xml`, `.json` |

The parser automatically detects the file type and extracts text content. To build without multi-format support (smaller image):

```bash
docker build --build-arg INSTALL_UNSTRUCTURED=false -t data_ingestor:slim .
```

## Supported Vector Stores

| Store | Description |
|-------|-------------|
| `qdrant` | Qdrant vector database |

## Supported Chunkers

| Chunker | Description |
|---------|-------------|
| `json` | JSON structure-aware chunking (splits arrays, objects) |

## Usage

The data ingestor is designed to run alongside a vector database via docker compose. Use `docker compose run` to execute it within the compose network so it can reach the vector_db service by name.

```bash
# Ingest a single URL
docker compose run data_ingestor https://example.com

# Ingest multiple URLs
docker compose run data_ingestor \
  https://example.com \
  https://example.com/page2

# Ingest from a file
docker compose run \
  -v $(pwd)/urls.txt:/app/urls.txt \
  data_ingestor -f /app/urls.txt

# Specify collection name
docker compose run data_ingestor \
  -c my_collection \
  https://example.com

# Ingest a PDF file
docker compose run \
  -v $(pwd)/document.pdf:/data/document.pdf \
  data_ingestor /data/document.pdf

# Ingest multiple document types
docker compose run \
  -v $(pwd)/docs:/data \
  data_ingestor /data/report.pdf /data/notes.docx /data/data.xlsx

# Use JSON chunking for API responses
docker compose run data_ingestor \
  -k json \
  https://api.example.com/data.json
```

### Docker Compose

```yaml
services:
  vector_db:
    image: vector_db:latest
    ports:
      - "6333:6333"

  data_ingestor:
    image: data_ingestor:latest
    depends_on:
      - vector_db
    environment:
      - VECTOR_DB_HOST=vector_db
    volumes:
      - ./data/data_ingestor:/app/custom
```

## CLI Options

```
usage: ingestor.py [options] <source> [source ...]

positional arguments:
  sources               Sources to ingest (URLs, file paths, etc.)

options:
  -f, --file FILE       File containing sources (one per line)
  -t, --type TYPE       Source type (default: html)
  -s, --store STORE     Vector store type (default: qdrant)
  -c, --collection NAME Collection name (default: documents)
  -k, --chunker TYPE    Chunker type (default: none, use 'json' for JSON-aware chunking)
  --config PATH         Config file path
```

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customizations (defaults copied on first run) |

The custom directory contains:
- `config/` - Configuration files
- `parsers/` - Custom parser classes
- `embedders/` - Custom embedder classes
- `chunkers/` - Custom chunker classes

## Configuration

### Config File

Defaults are copied to `/app/custom/config/` on first run. Behavioral settings go here:

```yaml
# General settings
request_delay: 1.0

# Parser settings
html:
  user_agent: "MyBot/1.0"
  timeout: 30

# Embedder settings
qdrant:
  model_name: "all-MiniLM-L6-v2"
  batch_size: 32

# Chunker settings
json_chunker:
  max_chunk_size: 1000   # Maximum characters per chunk
  min_chunk_size: 100    # Minimum characters per chunk
  split_arrays: true     # Split array elements into separate chunks

# Unstructured parser settings (for PDF, DOCX, etc.)
unstructured:
  strategy: "auto"       # "auto", "fast", "hi_res", or "ocr_only"
  include_metadata: true # Include element type breakdown
```

### Environment Variables

Connection settings that vary between environments:

| Variable | Description | Default |
|----------|-------------|---------|
| `VECTOR_DB_HOST` | Qdrant server hostname | `localhost` |
| `VECTOR_DB_PORT` | Qdrant server port | `6333` |

## Adding New Parsers

Custom parsers can be added by placing Python files in the `/app/parsers` volume mount. On first run, the default parsers are copied there and can be used as examples.

1. Create a new file in the mounted `parsers/` directory (e.g., `pdf_parser.py`)

2. Implement a class inheriting from `BaseParser` that implments the core `source_type` property and the `parse` and `fetch` methods. E.g. for a PDF parser:


```python
from base import BaseParser, ParsedDocument

class PDFParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "pdf"

    def parse(self, content: bytes, source: str) -> ParsedDocument:
        text = extract_pdf_text(content) # To be implemented

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

The parse function should return a ParsedDocument object containing the extracted text and metadata.

3. The parser is automatically discovered and registered on container restart

## Adding New Embedders

Custom embedders can be added by placing Python files in the `/app/embedders` volume mount.

1. Create a new file in the mounted `embedders/` directory (e.g., `pinecone_embedder.py`)

2. Implement a class inheriting from `BaseEmbedder` that implments the core `store_type` property and the `embed` and `store` methods. E.g. for a Pinecone embedder:

```python
from base import BaseEmbedder
from parsers.base import ParsedDocument

class PineconeEmbedder(BaseEmbedder):
    def __init__(self, api_key: str = "", environment: str = ""):
        self.api_key = api_key
        self.environment = environment

    @property
    def store_type(self) -> str:
        return "pinecone"

    def embed(self, text: str) -> list[float]:
        # Generate embedding vector suitable for store - code goes here
        return embedding_vector

    def store(self, documents: list[ParsedDocument], collection_name: str) -> int:
        # Store documents in Pinecone - code goes here
        return len(documents)
```

3. The embedder is automatically discovered and registered on container restart

## Adding New Chunkers

Custom chunkers can be added by placing Python files in the `/app/chunkers` volume mount.

1. Create a new file in the mounted `chunkers/` directory (e.g., `text_chunker.py`)

2. Implement a class inheriting from `BaseChunker` that implements the core `chunker_type` property and the `chunk` method:

```python
from chunkers.base import BaseChunker
from parsers.base import ParsedDocument

class TextChunker(BaseChunker):
    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size

    @property
    def chunker_type(self) -> str:
        return "text"

    def chunk(self, document: ParsedDocument) -> list[ParsedDocument]:
        # Split document.content into chunks
        chunks = []
        content = document.content

        for i, start in enumerate(range(0, len(content), self.max_chunk_size)):
            chunk_content = content[start:start + self.max_chunk_size]
            chunk_doc = ParsedDocument(
                source=document.source,
                title=document.title,
                content=chunk_content,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": -1,  # Updated after all chunks created
                    "parent_source": document.source,
                },
                timestamp=document.timestamp,
                source_type=document.source_type,
            )
            chunks.append(chunk_doc)

        # Update total_chunks in all chunks
        for chunk in chunks:
            chunk.metadata["total_chunks"] = len(chunks)

        return chunks
```

3. The chunker is automatically discovered and registered on container restart
