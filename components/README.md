# Components

Components are single-purpose Docker services — the building blocks of the toolkit. Each one does one job well and is designed to be combined with others or used on its own.

Components are published as images to GHCR. To use one, reference its image in your `docker-compose.yaml` and mount a local directory to `/app/custom`. On first run, the component writes its default configuration and any extensibility code into that directory. You can modify those files, or add new implementations, without rebuilding the image.

## Available Components

| Component | Type | Description |
|-----------|------|-------------|
| [vector_db](vector_db/) | Service | Qdrant vector database with plugin support for collection setup and configuration |
| [data_ingestor](data_ingestor/) | Service | Fetches content from URLs or files, embeds it, and stores it in a vector database |
| [mcp_server](mcp_server/) | Service | Exposes vector database operations as MCP tools for AI agents |
| [vector_query](vector_query/) | CLI | Query and manage vector databases directly — useful for testing and exploration |

## How Components Work

Every component follows the same pattern:

1. **Run from a published image** — no build step required
2. **Mount a `code/` directory** to `/app/custom` — this is where defaults land on first run
3. **Customise by editing files** in that directory, or adding new ones — parsers, embedders, backends, tools, plugins
4. **Restart the service** for changes to take effect

Each component's README covers its specific configuration options, environment variables, ports, and extension points.

## Building Your Own

New components follow the same conventions. See the [contributing guide](../docs/contributing_components.md) for templates, structure requirements, and the plugin pattern.
