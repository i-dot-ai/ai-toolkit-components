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

## Templates

Ready-to-use starting-point files are provided in `templates/component/`:

| File | Purpose |
|------|---------|
| [`templates/component/Dockerfile`](templates/component/Dockerfile) | Annotated Dockerfile covering the full component pattern |
| [`templates/component/entrypoint.sh`](templates/component/entrypoint.sh) | Annotated entrypoint script with the copy-on-first-run loop |
| [`templates/component/src/config/config.yaml`](templates/component/src/config/config.yaml) | Starter config file with guidance on what belongs here |
| [`templates/component/README.md`](templates/component/README.md) | README template with all required sections |

Copy these into your new component directory and replace the `COMPONENT_*` placeholders with values specific to your component.

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

Start from the template at [`templates/component/Dockerfile`](templates/component/Dockerfile).

Key conventions:
- Use `python:3.12-slim` (or a purpose-built slim base image) to keep image size small
- Always define a `HEALTHCHECK` if your component is a long-running service — this allows other services to declare `depends_on: condition: service_healthy`
- Use a single `/app/custom` mount point (see the [Customisation Pattern](#customisation-pattern) section below)
- Place defaults at `/app/defaults/` so they can be copied to `/app/custom` on first run

If your component does **not** run as a persistent service (i.e. it executes a task and exits), omit the `HEALTHCHECK`. The template marks these lines clearly.

### 3. Write the entrypoint.sh

Start from the template at [`templates/component/entrypoint.sh`](templates/component/entrypoint.sh).

The copy-on-first-run loop at the top copies default files from `/app/defaults/` into the mounted `/app/custom/` directory only if they are not already present. This means users can customise behaviour by editing files in the mounted volume without needing to rebuild the image, and their edits are never overwritten.

Extend the `SUBDIRS` array in the template for each plugin directory your component exposes (e.g. `parsers`, `backends`).

### 4. Write the Source Code

Read configuration from `/app/custom/config/config.yaml` at startup. Connection details (hostnames, ports, credentials) should come from environment variables rather than config files, so that the same image works in different environments.

#### Making Your Component Extensible (Optional)

If your component benefits from a **plugin architecture** (e.g. support for multiple backends or content types), follow the pattern used by `data_ingestor` and `mcp_server`:

1. Define an abstract base class in `src/<plugin_type>/base.py`
2. Ship built-in implementations alongside it
3. Copy all of `src/<plugin_type>/` to `/app/defaults/<plugin_type>/` in the Dockerfile
4. Use the shared `PluginRegistry` class from `registry.py` to auto-discover subclasses at runtime

This lets users add new implementations by dropping Python files into the mounted volume, without modifying the image.

See `components/data_ingestor/src/registry.py` for the registry implementation and `components/data_ingestor/src/parsers/base.py` for an example base class.

### 5. Provide a Default Config

Start from the template at [`templates/component/src/config/config.yaml`](templates/component/src/config/config.yaml).

Keep this file to **behavioural** settings (batch sizes, timeouts, model names, feature flags). Do not put hostnames, ports, or credentials here — use environment variables for those.

### 6. Register in docker-compose.yaml

Add your component to the root `docker-compose.yaml` so it can be built and tested locally. Resource limits (`deploy.resources`) are mandatory — they prevent runaway containers from consuming all available memory or CPU on the host. See the existing component entries for the expected structure.

### 7. Write a README

Start from the template at [`templates/component/README.md`](templates/component/README.md). It contains all required sections: features, usage, volume mounts, configuration, and ports. See `components/data_ingestor/README.md` or `components/mcp_server/README.md` for completed examples.

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

Unit tests live in `tests/unit/test_<component_name>.py`. They test your Python logic in isolation — no Docker required. Mock any heavy dependencies (database clients, HTTP calls, model loading).

Run them with:

```bash
./run_tests.sh unit <component_name>
```

### Component Tests

Component tests live in `tests/components/test_<component_name>.py`. They build and start the actual Docker container, then verify it behaves correctly over the network. They use the `component_endpoint` pytest fixture, which handles build, start, and teardown automatically.

The fixture is parametrised with a `(service_name, internal_port)` tuple — see the existing component tests under `tests/components/` for the pattern.

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
