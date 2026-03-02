# COMPONENT_NAME  <!-- TODO: replace with your component's display name -->

<!-- TODO: One sentence describing what the component does. -->

## Features

<!-- TODO: Bullet-point list of key capabilities. -->

- TODO

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](../../docs/prerequisites.md) for installation instructions.

## Usage

<!-- TODO: Show how to include this component in a docker-compose.yaml.
     Replace COMPONENT_NAME, HOST_PORT, and CONTAINER_PORT. -->

```yaml
services:
  COMPONENT_NAME:
    image: ghcr.io/i-dot-ai/ai-toolkit-COMPONENT_NAME:latest
    container_name: COMPONENT_NAME
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

<!-- TODO: Add any usage instructions specific to your component, such as
     CLI commands (for run-once tasks) or API examples (for services). -->

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customisations (defaults copied on first run) |

The custom directory contains:

<!-- TODO: List the subdirectories that appear after first run. -->

- `config/` — Configuration files
- `requirements.txt` — Python packages; append here and restart to install extras
<!-- - `plugins/` — Startup scripts run once after the service starts -->
<!-- - `EXTENSION_DIR/` — Custom EXTENSION_TYPE classes, auto-discovered at startup -->

## Configuration

### Config File

Defaults are copied to `/app/custom/config/` on first run. Edit them there — the originals in the image are never overwritten.

<!-- TODO: Show the key settings from your config.yaml with brief comments. -->

```yaml
# TODO: example settings
```

### Environment Variables

<!-- TODO: List all environment variables your component reads. -->

| Variable | Description | Default |
|----------|-------------|---------|
| `SOME_VAR` | TODO: what it does | `default_value` |

## Ports

<!-- TODO: List every port the component exposes. Remove this section for run-once tasks. -->

| Port | Protocol | Description |
|------|----------|-------------|
| `PORT` | HTTP | TODO: description |

## Customisation

<!-- TODO: If your component supports extensibility extensions or startup plugins,
     explain how users add their own. Remove this section if it does not apply.

     For extensibility extensions, show a minimal example class:

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
        ...
```

     For startup plugins, show a minimal example:

### Adding Startup Plugins

Drop a `.py` file into `code/COMPONENT_NAME/plugins/`. It runs once after the service starts.

```python
def main():
    # setup logic here
    pass

if __name__ == "__main__":
    main()
```
-->

## Resource Limits

<!-- TODO: Fill in the resource limits that match your docker-compose.yaml entry. -->

| Memory Limit | CPU Limit |
|--------------|-----------|
| 2GB | 1 core |
