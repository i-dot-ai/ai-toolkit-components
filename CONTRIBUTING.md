# Contributing a New Component

This guide walks you through the process of packaging a piece of functionality as a component and contributing it to this repository.

## What is a Component?

A **component** is a standalone Docker service that does one thing well. It lives in `components/<name>/` and is independently buildable, testable, and deployable. Components are the building blocks that applications wire together via docker-compose.

Good candidates for components are:
- A wrapper around an existing service (e.g. a vector database, a message broker)
- A data processing pipeline stage (e.g. an ingestor, a transformer)
- An API gateway or protocol adapter (e.g. an MCP server, a REST proxy)

## Prerequisites

- Docker and Docker Compose installed
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12+
- Dependencies installed (`uv sync`)

---

## Component Structure

Every component follows this layout:

```
components/<component_name>/
├── Dockerfile          # Build definition
├── entrypoint.sh       # Container startup script
├── README.md           # Component documentation
└── src/
    ├── <main>.py       # Core application logic
    ├── config/
    │   └── config.yaml # Default configuration
    └── ...             # Additional source files
```

The `Dockerfile` and `entrypoint.sh` are mandatory. Everything else depends on what your component does.

---

## Step-by-Step Guide

### 1. Create the Directory

```bash
mkdir -p components/<component_name>/src/config
```

Use `snake_case` for the component name (e.g. `document_chunker`, `pdf_parser`).

### 2. Write the Dockerfile

Components follow a consistent pattern:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (keep minimal)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    pyyaml \
    requests

# Copy entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy application source
COPY src/<main>.py /app/

# Copy customisable defaults (will be copied to /app/custom on startup)
COPY src/config/ /app/defaults/config/

# Create the single user-customisation mount point
RUN mkdir -p /app/custom

# Health check so dependent services can wait for readiness
HEALTHCHECK --interval=5s --timeout=3s --retries=12 \
  CMD curl -f http://localhost:<port>/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
```

Key conventions:
- Use `python:3.12-slim` (or a purpose-built slim base image) to keep image size small
- Always define a `HEALTHCHECK` if your component is a long-running service — this allows other services to declare `depends_on: condition: service_healthy`
- Use a single `/app/custom` mount point (see the [Customisation Pattern](#customisation-pattern) section below)
- Place defaults at `/app/defaults/` so they can be copied to `/app/custom` on first run

If your component does **not** run as a persistent service (i.e. it executes a task and exits), omit the `HEALTHCHECK`.

### 3. Write the entrypoint.sh

The entrypoint follows a standard structure:

```bash
#!/bin/bash
set -e

CUSTOM_DIR="/app/custom"
SUBDIRS=("config")  # Add any other customisable subdirectories here

# Copy defaults to /app/custom if not already present
for dir in "${SUBDIRS[@]}"; do
    mkdir -p "$CUSTOM_DIR/$dir"

    if [ -d "/app/defaults/$dir" ]; then
        for file in /app/defaults/$dir/*.py /app/defaults/$dir/*.yaml; do
            [ -e "$file" ] || continue
            base_file=$(basename "$file")
            dest_file="$CUSTOM_DIR/$dir/$base_file"

            if [ ! -e "$dest_file" ]; then
                echo "Copying default: $dir/$base_file"
                cp "$file" "$dest_file"
            fi
        done
    fi
done

echo "Starting <component_name>..."

# For persistent services:
exec python -u /app/<main>.py

# For run-once tasks, pass through CLI arguments:
# exec python -u /app/<main>.py "$@"
```

The copy-on-first-run pattern means users can customise behaviour by editing files in the mounted volume without needing to rebuild the image.

### 4. Write the Source Code

Structure your code to read configuration from `/app/custom/config/config.yaml` at startup. Connection details (hostnames, ports, credentials) should come from environment variables rather than config files, so that the same image works in different environments.

```python
import os
import yaml

def load_config(path="/app/custom/config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f) or {}

config = load_config()

# Behavioural settings from YAML
batch_size = config.get("batch_size", 32)

# Infrastructure settings from environment variables
db_host = os.getenv("DB_HOST", "localhost")
db_port = int(os.getenv("DB_PORT", "5432"))
```

#### Making Your Component Extensible (Optional)

If your component benefits from a **plugin architecture** (e.g. support for multiple backends or content types), follow the pattern used by `data_ingestor` and `mcp_server`:

1. Define an abstract base class in `src/<plugin_type>/base.py`
2. Ship built-in implementations alongside it
3. Copy all of `src/<plugin_type>/` to `/app/defaults/<plugin_type>/` in the Dockerfile
4. Use the shared `PluginRegistry` class from `registry.py` to auto-discover subclasses at runtime

This lets users add new implementations by dropping Python files into the mounted volume, without modifying the image.

See `components/data_ingestor/src/registry.py` for the registry implementation and `components/data_ingestor/src/parsers/base.py` for an example base class.

### 5. Provide a Default Config

Create `src/config/config.yaml` with sensible defaults and clear comments:

```yaml
# Behavioural settings for <component_name>
batch_size: 32
timeout: 30

# Add further settings here
```

Do not put hostnames, ports, or credentials in this file — use environment variables for those.

### 6. Register in docker-compose.yaml

Add your component to the root `docker-compose.yaml` so it can be built and tested locally:

```yaml
services:
  <component_name>:
    build:
      context: components/<component_name>
      dockerfile: Dockerfile
    container_name: <component_name>
    ports:
      - "<host_port>:<container_port>"
    volumes:
      - ./components/<component_name>/src/custom:/app/custom
    environment:
      - SOME_ENV_VAR=value
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1.0"
        reservations:
          memory: 512M
          cpus: "0.5"
```

Resource limits are mandatory — they prevent runaway containers from consuming all available memory or CPU on the host.

---

## Customisation Pattern

Every component exposes a **single volume mount point** at `/app/custom`. The entrypoint copies the bundled defaults into this directory on first run (if the files are not already present). This means:

- Users who just want defaults need only mount the volume — no configuration required
- Users who want to customise can edit the files that appear in the mounted directory after the first run
- The image itself never needs to be rebuilt for configuration changes

The contents of `/app/custom` depend on the component, but always include a `config/` subdirectory. Additional subdirectories are added for each type of extensible plugin (e.g. `parsers/`, `tools/`, `backends/`).

---

## Writing Tests

All components require tests at two levels. The CI pipelines automatically discover test files by name, so following the naming convention is essential.

### Unit Tests

Unit tests live in `tests/unit/test_<component_name>.py`. They test your Python logic in isolation — no Docker required. Mock any heavy dependencies (database clients, HTTP calls, model loading):

```python
# tests/unit/test_<component_name>.py
from unittest.mock import MagicMock, patch
import pytest

def test_config_loading():
    config = {"batch_size": 16}
    # ... test your config loading logic

def test_core_logic():
    # ... test the business logic
```

Run them with:

```bash
./run_tests.sh unit <component_name>
# or
uv run pytest -v tests/unit/test_<component_name>.py
```

### Component Tests

Component tests live in `tests/components/test_<component_name>.py`. They build and start the actual Docker container, then verify it behaves correctly over the network. They use the `component_endpoint` pytest fixture, which handles build, start, and teardown automatically.

```python
# tests/components/test_<component_name>.py
import pytest
import requests

@pytest.fixture(scope="module", params=[("<component_name>", <port>)])
def component_endpoint(component_endpoint):
    return component_endpoint

def test_health_check(component_endpoint):
    response = requests.get(f"{component_endpoint}/health")
    assert response.status_code == 200

def test_core_functionality(component_endpoint):
    # ... test your component's API
```

The `params` tuple must be `(service_name_in_docker_compose, internal_port)`.

Run them with:

```bash
./run_tests.sh component <component_name>
```

### What to Test

At minimum, component tests should verify:
- The health endpoint returns HTTP 200 (if applicable)
- The primary API or function works correctly end-to-end
- Error cases return appropriate responses

---

## Writing a README

Every component needs a `README.md`. Use this structure:

```markdown
# <Component Name>

One sentence describing what the component does.

## Features

- Bullet points of key capabilities

## Usage

Show the minimal docker-compose snippet to use this component.

## Volume Mounts

| Path | Description |
|------|-------------|
| `/app/custom` | User customisations (defaults copied on first run) |

Document the subdirectories and what can be customised in each.

## Configuration

### Config File
Document the config.yaml options with examples.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SOME_VAR` | What it does | `default_value` |

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| `8080` | HTTP | REST API |
```

---

## Pull Request Checklist

Before opening a PR, verify that:

- [ ] `components/<name>/Dockerfile` exists and builds successfully
- [ ] `components/<name>/entrypoint.sh` exists and is executable
- [ ] Component is added to the root `docker-compose.yaml` with resource limits
- [ ] `tests/unit/test_<name>.py` exists and passes (`./run_tests.sh unit <name>`)
- [ ] `tests/components/test_<name>.py` exists and passes (`./run_tests.sh component <name>`)
- [ ] `components/<name>/README.md` documents usage, configuration, and volume mounts
- [ ] All GitHub Actions pass on the PR

The CI pipelines discover components and tests automatically by scanning directory and file names — no pipeline configuration changes are needed.

---

## CI/CD Overview

The following workflows run automatically on every pull request:

| Workflow | What it does |
|----------|-------------|
| `unit-tests.yml` | Runs `tests/unit/test_<name>.py` for each component in parallel |
| `component-build-test.yml` | Builds each component's Docker image and runs `tests/components/test_<name>.py` |
| `application-test.yml` | Runs `tests/applications/test_<name>.py` for each application after component builds succeed |

On merge to `main`, a `publish-latest.yml` workflow automatically pushes a `latest`-tagged image to GHCR (`ghcr.io/i-dot-ai/ai-toolkit-<component_name>`). Versioned releases are created manually via the `release.yml` workflow.
