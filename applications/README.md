# Applications

Applications are complete, ready-to-run solutions built by combining components. Each one is a `docker-compose.yaml` that wires published component images together — no source code required to run them.

Copy an application's `docker-compose.yaml` to your working directory, run `docker compose up -d`, and you have a working stack. On first run, each component writes its default configuration into a `code/` subdirectory. Edit those files to customise behaviour without rebuilding anything.

## Available Applications

| Application | Description |
|-------------|-------------|
| [mcp_datastore](mcp_datastore/) | Ingest documents, search them by meaning, and give AI agents direct access via MCP |

## Building Your Own

If none of the existing applications fit your needs, you can compose your own from the available [components](../components/) by writing a `docker-compose.yaml` that references the images you need. See the [development guide](../docs/development.md) and [contributing guide](../docs/contributing_applications.md) for conventions and templates.
