# COMPONENT_NAME  <!-- TODO: replace with your component's display name (Title Case, spaces not underscores) -->

<!-- TODO: One sentence describing what this component does.
     Start with "A containerised <noun phrase>" and focus on what it provides to the user,
     not how it works internally. Examples:
       "A containerised MCP server that exposes vector database operations as tools for AI agents."
       "A containerised service for ingesting content from various sources and embedding it into vector databases."
-->

## Features

<!-- TODO: Bullet-point list of key capabilities — what a user can do with this component.
     Aim for 4–6 bullets. Focus on user-visible behaviour, not implementation details.
     Lead with the most distinctive capability. Examples:
       "- Pluggable backend architecture — support for multiple vector databases"
       "- Auto-discovery of parser and embedder classes"
       "- Configurable via YAML and environment variables"
     If this component exposes a well-defined set of operations (tools, endpoints, CLI flags),
     add a table below the bullets — see mcp_server/README.md for an example.
-->

- TODO

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](../../docs/prerequisites.md) for installation instructions.

## Usage

<!-- TODO: Show how to include this component in a docker-compose.yaml.
     Replace COMPONENT_NAME with the snake_case component directory name.
     The image name uses kebab-case: ghcr.io/i-dot-ai/ai-toolkit-COMPONENT-NAME:latest
     HOST_PORT is the port exposed on the developer's machine; CONTAINER_PORT is what the
     process inside the container binds to (these are often the same value).
     If this component must run alongside others (e.g. a vector_db), show a multi-service
     compose snippet with depends_on — see mcp_server/README.md for an example.
     Remove the ports entry entirely if this component exposes no network ports. -->

### Using the Published Image

To run the service using the published docker image, add the below snippet to your docker compose file:

```yaml
services:
  COMPONENT_NAME:
    image: ghcr.io/i-dot-ai/ai-toolkit-COMPONENT_NAME:latest
    container_name: COMPONENT_NAME
    restart: unless-stopped
    volumes:
      - ./code/COMPONENT_NAME:/app/custom
    ports:
      - "HOST_PORT:CONTAINER_PORT"  # TODO: remove if this component exposes no ports
    # TODO: add environment variables your component needs, e.g.:
    # environment:
    #   - SOME_HOST=other_service
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
        reservations:
          memory: 1G
          cpus: "0.5"
```

<!-- TODO: If this component depends on other services (e.g. vector_db), add a note here:
     "Note that this includes the `vector_db` component — if you wish to run alongside an
     alternative database you can replace that section." -->

The services can then be run via:

```bash
docker compose up -d COMPONENT_NAME
```

<!-- TODO: If a multi-service snippet is shown above, also add:
Or to run just the `COMPONENT_NAME`:

```bash
docker compose up -d COMPONENT_NAME
```
-->

### Building from Source

To build and run from source, add the below snippet to your docker compose file:

```yaml
services:
  COMPONENT_NAME:
    build:
      context: .
      dockerfile: components/COMPONENT_NAME/Dockerfile
    container_name: COMPONENT_NAME
    restart: unless-stopped
    volumes:
      - ./code/COMPONENT_NAME:/app/custom
    ports:
      - "HOST_PORT:CONTAINER_PORT"  # TODO: remove if this component exposes no ports
    # TODO: add environment variables your component needs, e.g.:
    # environment:
    #   - SOME_HOST=other_service
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1.0"
        reservations:
          memory: 1G
          cpus: "0.5"
```

<!-- TODO: Repeat the vector_db note here if applicable. -->

Then build and start the service:

```bash
docker compose build COMPONENT_NAME
docker compose up -d COMPONENT_NAME
```

<!-- TODO: If a multi-service snippet is shown above, also add:
Or to build and run just the `COMPONENT_NAME`:

```bash
docker compose build COMPONENT_NAME
docker compose up -d COMPONENT_NAME
```
-->

### <Optional Usage Guide>


<!-- TODO: Add usage instructions specific to your component. Choose the style that fits:
     - HTTP service: show a curl health check, then the key API or MCP client endpoints.
     - CLI component: show docker compose exec examples for the most common invocations,
       then add a "CLI Options" section with the full usage string (run with --help to get it).
       See data_ingestor/README.md for an example.
     - Background/daemon with no user-facing interface: explain how to verify it started
       (health endpoint or log output).
-->

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customisations (defaults copied on first run) |

The custom directory contains:

<!-- TODO: List only the subdirectories that actually appear after first run.
     Keep config/ and requirements.txt — they are present in every component.
     Uncomment the lines below that apply, and add any component-specific directories.
     Each extension directory (parsers/, backends/, etc.) should have its own entry. -->

- `config/` — Configuration files
- `requirements.txt` — Python packages; append here and restart to install extras
<!-- - `plugins/` — Startup scripts run once after the service starts -->
<!-- - `EXTENSION_DIR/` — Custom EXTENSION_TYPE classes, auto-discovered at startup -->

## Configuration

### Config File

Defaults are copied to `/app/custom/config/` on first run. Edit them there — the originals in the image are never overwritten.

<!-- TODO: Show the key settings from your config.yaml with inline comments explaining each one.
     Include every setting a user is likely to want to change. Omit internal/advanced settings
     that most users will never touch. See data_ingestor/README.md for an example. -->

```yaml
# TODO: example settings
```

### Environment Variables

<!-- TODO: List every environment variable the component reads, including optional ones.
     Use the same variable names as in the entrypoint.sh / source code.
     Split into two groups if it helps: connection settings (host/port of dependencies)
     and behavioural settings (feature flags, limits). See mcp_server/README.md for an example. -->

| Variable | Description | Default |
|----------|-------------|---------|
| `SOME_VAR` | TODO: what it does | `default_value` |

## Ports

<!-- TODO: List every port the component exposes, matching the CONTAINER_PORT values in your
     docker-compose snippets above. Remove this entire section if the component exposes no ports
     (e.g. CLI tools or background workers that only connect outbound). -->

| Port | Protocol | Description |
|------|----------|-------------|
| `PORT` | HTTP | TODO: description |

## Customisation

<!-- TODO: Include this section if the component supports user-supplied extensions or plugins.
     Remove it entirely if there is no extensibility mechanism.

     For each extension point, add a subsection (H3) following this pattern:
       1. One sentence explaining what this extension point is for.
       2. Where to drop the file (the volume-mounted directory).
       3. A minimal working example class with the required property and one key method.
       4. One sentence explaining auto-discovery ("discovered on container restart").
     See mcp_server/README.md (Adding Custom Backends/Tools) and
     data_ingestor/README.md (Adding New Parsers/Embedders) for complete examples.

     For each extension type, fill in:
       EXTENSION_TYPE  — plural display name, e.g. "Backends", "Parsers"
       EXTENSION_DIR   — directory name, e.g. "backends", "parsers"
       BaseEXTENSION   — base class name, e.g. "BaseBackend", "BaseParser"
       extension_type  — the string identifier property, e.g. "qdrant", "pdf"
-->

### Adding Custom EXTENSION_TYPEs

Drop a `.py` file into `code/COMPONENT_NAME/EXTENSION_DIR/`. It is auto-discovered on container restart.

The file must define a class that inherits from `BaseEXTENSION` and implements the required methods:

```python
from base import BaseEXTENSION

class MyEXTENSION(BaseEXTENSION):
    @property
    def extension_type(self) -> str:
        return "my_type"

    def my_method(self, ...):
        # implementation here
        ...
```

### Adding Startup Plugins

<!-- TODO: Remove this subsection if the component does not support startup plugins. -->

Drop a `.py` file into `code/COMPONENT_NAME/plugins/`. It runs once after the service starts.

```python
def main():
    # setup logic here
    pass

if __name__ == "__main__":
    main()
```

## Resource Limits

<!-- TODO: Update these values to match the limits in your docker-compose.yaml entry.
     If the component is CPU- or memory-intensive (e.g. runs an embedding model), increase
     accordingly and note why in the Dockerfile or entrypoint comments. -->

| Memory Limit | CPU Limit |
|--------------|-----------|
| 2GB | 1 core |
