# AI Toolkit Components Repository

Build AI-powered applications faster with ready-to-use, containerised building blocks.

Use it to build things like: a semantic search tool over your documents, an AI agent that can query your knowledge base via MCP, or a document ingestion pipeline — without wiring up a vector database, embedding models, or an MCP server from scratch.

## Why use this?

Building AI applications from open-source tools typically means significant integration work before you have something you can actually build on top of: picking the right tools, wiring them together, building configuration and extension patterns, writing the glue code, and keeping everything working as requirements change.

This toolkit takes a different approach. Each component handles one job and is already integrated with the others. You get:

- **Running in minutes, not weeks.** Published Docker images mean `docker compose up` is all you need. No build pipeline, no glue code.
- **Customisable without forking.** Every component copies its default configuration and extension code into a mounted volume on first run. Add or swap implementations by dropping a file in a directory — no image rebuild required.
- **Composable.** Use a complete application stack, or pick only the components you need. If you have strong opinions about one part of the stack, write a custom implementation that plugs in to the rest.
- **Consistent patterns.** Every component follows the same conventions for configuration, extension, and testing, so there is less to learn each time you add or modify one.

The components are designed to be used as-is or as a starting point — working integrations out of the box, with clear extension points wherever you need to diverge from the defaults. Building the same stack from scratch means handling the full infrastructure and integration work yourself.

## What Is This?

This repository provides **components** and **applications** that you can use to quickly assemble AI solutions without starting from scratch.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            APPLICATIONS                                 │
│         Complete solutions built by combining components                │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  mcp_datastore                                                    │  │
│  │  A document ingestion and semantic search application             │  │
│  │                                                                   │  │
│  │    ┌─────────────────┐          ┌─────────────────┐               │  │
│  │    │  data_ingestor  │ ──────▶  │    vector_db    │               │  │
│  │    │                 │          │                 │               │  │
│  │    │  • Parse HTML   │  embed   │  • Store vectors│               │  │
│  │    │  • Embed content│  ─────▶  │  • Search       │               │  │
│  │    │                 │          │  • Query API    │               │  │
│  │    └─────────────────┘          └───────┬─────────┘               │  │
│  │         COMPONENT                       │ COMPONENT               │  │
│  │                                         │                         │  │
│  │                                  ┌──────┴──────────┐              │  │
│  │                                  │   mcp_server    │              │  │
│  │                                  │                 │              │  │
│  │                                  │  • MCP protocol │              │  │
│  │                                  │  • AI agent API │              │  │
│  │                                  └─────────────────┘              │  │
│  │                                       COMPONENT                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  vector_query  (standalone component — not part of the app pipeline)    │
│  CLI for querying and managing vector databases directly                │
│  Useful for testing, exploration, and scripting without an MCP client   │
└─────────────────────────────────────────────────────────────────────────┘

COMPONENTS = Independent, reusable Docker services (the building blocks)
APPLICATIONS = docker-compose orchestrations that wire components together
```

**Components** are standalone Docker services that do one thing well. They're published as images to GHCR and designed to be mixed and matched.

**Applications** are complete solutions that combine components using docker-compose. Copy an application's `docker-compose.yaml` to your project and you're ready to go — no cloning required.

## Getting Started

| I want to... | Go to... |
|--------------|----------|
| **Run an existing application** | [Quick Start](#quick-start) |
| **Build a new application from components** | [Quick Start → Build a new application](#build-a-new-application-from-components) |
| **Use a component in your own stack** | [Components](#components) |
| **Build applications or modify components** | [Development guide](docs/development.md) |
| **Build components and/or contribute back** | [Contributing](docs/contributing.md) |

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](docs/prerequisites.md) for installation instructions for macOS, Windows, and Linux.

---

## Quick Start

### Run an existing application

Copy an application's `docker-compose.yaml` to your working directory and start it:

```bash
cp applications/mcp_datastore/docker-compose.yaml .
docker compose up -d
```

Docker pulls the published images automatically — no source code or build step needed. On first run, each component writes its default configuration into a `code/` directory. Edit those files to customise behaviour, then restart the relevant service.

See the application's README for full usage instructions, including how to ingest content and connect an AI agent.

### Build a new application from components

Create a `docker-compose.yaml` that references the published component images you need:

```yaml
services:
  vector_db:
    image: ghcr.io/i-dot-ai/ai-toolkit-vector-db:latest
    ports:
      - "6333:6333"
    volumes:
      - ./code/vector_db:/app/custom

  data_ingestor:
    image: ghcr.io/i-dot-ai/ai-toolkit-data-ingestor:latest
    depends_on:
      vector_db:
        condition: service_healthy
    environment:
      - VECTOR_DB_HOST=vector_db
      - VECTOR_DB_PORT=6333
    volumes:
      - ./code/data_ingestor:/app/custom
```

Then start it:

```bash
docker compose up -d
```

Each component mounts a `code/` subdirectory where its default configuration and any extensibility code are written on first run. See each component's README for the full list of environment variables, ports, and customisation options.

---

## Applications

Applications are complete, ready-to-run solutions. Each is a `docker-compose.yaml` that wires published component images together.

| Application | Description |
|-------------|-------------|
| [mcp_datastore](applications/mcp_datastore/) | Document ingestion and semantic search with MCP agent access |

---

## Components

Components are single-purpose Docker services. Use them individually in your own `docker-compose.yaml`, or combine them into a custom application.

| Component | Description |
|-----------|-------------|
| [vector_db](components/vector_db/) | Qdrant vector database with plugin support |
| [data_ingestor](components/data_ingestor/) | Content ingestion and embedding |
| [mcp_server](components/mcp_server/) | MCP server exposing vector DB tools for AI agents |
| [vector_query](components/vector_query/) | CLI for querying and managing vector databases directly |

Each component's README covers its available image, configuration options, and how to extend it via mounted volumes.


## Contributing

See [Contributing](docs/contributing.md) for a full guide on adding new components and applications.

See [LICENSE](LICENSE) for terms.
