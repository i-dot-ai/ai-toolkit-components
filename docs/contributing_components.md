# Contributing: Adding a New Component

Components are standalone Docker services that do one thing well — the building blocks of the AI Toolkit.

## Prerequisites

See the [Prerequisites guide](prerequisites.md) for full installation instructions. You will need:

- Docker and Docker Compose
- Python 3.12+
- `uv` (the project's package manager)
- Project dependencies installed with `uv sync`

---

## Templates

Ready-to-use starting-point files are provided in `templates/component/`:

| File | Purpose |
|------|---------|
| [`templates/component/Dockerfile`](../templates/component/Dockerfile) | Annotated Dockerfile covering the full component pattern |
| [`templates/component/entrypoint.sh`](../templates/component/entrypoint.sh) | Annotated entrypoint script with the copy-on-first-run loop |
| [`templates/component/src/requirements.txt`](../templates/component/src/requirements.txt) | Python dependencies — edit in the mounted volume to add packages without rebuilding |
| [`templates/component/src/registry.py`](../templates/component/src/registry.py) | Generic `PluginRegistry` for auto-discovering extensibility subclasses |
| [`templates/component/src/plugins/example_plugin.py`](../templates/component/src/plugins/example_plugin.py) | Example startup script (run once by the entrypoint after the service starts) |
| [`templates/component/src/extensions/base.py`](../templates/component/src/extensions/base.py) | Abstract base class template for extensibility extensions |
| [`templates/component/src/extensions/__init__.py`](../templates/component/src/extensions/__init__.py) | Wires up the `PluginRegistry` and exposes the public lookup API |
| [`templates/component/src/config/config.yaml`](../templates/component/src/config/config.yaml) | Starter config file with guidance on what belongs here |
| [`templates/component/README.md`](../templates/component/README.md) | README template with all required sections |

Copy these into your new component directory and replace the `COMPONENT_*` placeholders with values specific to your component.

## Structure

Every component follows this layout:

```
components/<component_name>/
├── Dockerfile           # Build definition
├── entrypoint.sh        # Container startup script
├── README.md            # Component documentation
└── src/
    ├── <main>.py        # Core application logic
    ├── requirements.txt # Python dependencies (editable at runtime via mounted volume)
    ├── registry.py      # Plugin registry — include if using extensibility extensions
    ├── config/
    │   └── config.yaml  # Default configuration
    ├── plugins/         # Startup scripts — include if using the startup script pattern
    │   └── example_plugin.py
    └── extensions/      # Extensibility classes — include if using the extensibility pattern
        ├── __init__.py
        └── base.py
```

The `Dockerfile`, `entrypoint.sh`, and `src/requirements.txt` are mandatory. Everything else depends on what your component does.

## Step-by-Step Guide

### 1. Create the directory

```bash
mkdir -p components/<component_name>/src/config
```

Use `snake_case` for the component name (e.g. `document_chunker`, `pdf_parser`). If you plan to expose a plugin directory to users (see [Plugin Patterns](#plugin-patterns)), create it now:

```bash
# For startup scripts (simple .py files run by the entrypoint on startup):
mkdir -p components/<component_name>/src/plugins

# For extensibility extensions (class-based, auto-discovered via PluginRegistry):
mkdir -p components/<component_name>/src/<extension_type>
```

### 2. Write the Dockerfile

Start from the template at [`templates/component/Dockerfile`](../templates/component/Dockerfile).

Key conventions:
- Use `python:3.12-slim` (or a purpose-built slim base image) to keep image size small
- List Python dependencies in `src/requirements.txt` — the Dockerfile installs from it at build time, and the entrypoint copies it to the mounted volume so users can add packages without rebuilding
- Always define a `HEALTHCHECK` if your component is a long-running service — this allows other services to declare `depends_on: condition: service_healthy`
- Use a single `/app/custom` mount point (see [Customisation Pattern](#customisation-pattern) below)
- Place defaults at `/app/defaults/` so they can be copied to `/app/custom` on first run

If your component does **not** run as a persistent service (i.e. it executes a task and exits), omit the `HEALTHCHECK`. The template marks these lines clearly.

### 3. Write the entrypoint.sh

Start from the template at [`templates/component/entrypoint.sh`](../templates/component/entrypoint.sh).

The entrypoint does two things at startup:

1. **Copies defaults** — files from `/app/defaults/` are copied to `/app/custom/` only if not already present, so user edits are never overwritten. Extend the `SUBDIRS` array for each plugin directory your component exposes.
2. **Installs packages** — `requirements.txt` is copied to `/app/custom/` on first run, then `pip install -r /app/custom/requirements.txt` runs on every startup. When a user appends a package and restarts, it is installed automatically.

### 4. Write the source code

Read configuration from `/app/custom/config/config.yaml` at startup. Connection details (hostnames, ports, credentials) should come from environment variables rather than config files, so that the same image works in different environments.

If your component benefits from a plugin architecture, see [Plugin Patterns](#plugin-patterns).

### 5. Provide a default config

Start from the template at [`templates/component/src/config/config.yaml`](../templates/component/src/config/config.yaml).

Keep this file to **behavioural** settings (batch sizes, timeouts, model names, feature flags). Do not put hostnames, ports, or credentials here — use environment variables for those.

### 6. Register in docker-compose.yaml

Add your component to the root `docker-compose.yaml` so it can be built and tested locally. Resource limits (`deploy.resources`) are mandatory — they prevent runaway containers from consuming all available memory or CPU on the host. See the existing component entries for the expected structure.

### 7. Write a README

Start from the template at [`templates/component/README.md`](../templates/component/README.md). It contains all required sections: features, usage, volume mounts, configuration, and ports. See `components/data_ingestor/README.md` or `components/mcp_server/README.md` for completed examples.

## Customisation Pattern

Every component exposes a **single volume mount point** at `/app/custom`. The entrypoint copies the bundled defaults into this directory on first run (if the files are not already present). This means:

- Users who just want defaults need only mount the volume — no configuration required
- Users who want to customise can edit the files that appear in the mounted directory after the first run
- The image itself never needs to be rebuilt for configuration changes or extra packages

The contents of `/app/custom` always include:
- `config/` — YAML configuration files
- `requirements.txt` — Python packages; append to this file and restart to install extras
- Additional subdirectories for any plugin types the component exposes

## Plugin Patterns

There are two distinct plugin patterns used across the components. Choose based on what you need.

### Startup scripts

Used by `vector_db`. The entrypoint runs every `.py` file in the `plugins/` directory after the service starts. Each script is a standalone Python file with no required base class or interface.

This is suited to **one-time setup tasks** — creating database collections, seeding initial data, configuring indexes — that must run before the service is usable.

To use this pattern:
1. Create `src/plugins/` and copy in `templates/component/src/plugins/example_plugin.py`
2. In the Dockerfile, copy `src/plugins/` to `/app/defaults/plugins/`
3. In the entrypoint, add `"plugins"` to `SUBDIRS` and uncomment the startup script execution loop

See `components/vector_db/entrypoint.sh` for the execution loop.

### Extensibility extensions

Used by `data_ingestor` (parsers, embedders) and `mcp_server` (tools, backends). Extensions are Python classes that inherit from an abstract base class and are auto-discovered at startup by `PluginRegistry`. Users add new implementations by dropping a `.py` file into the mounted volume.

This is suited to **adding new capabilities at runtime** — new content parsers, database backends, API tools — without modifying the image.

To use this pattern:
1. Copy `templates/component/src/registry.py` and `templates/component/src/extensions/` into your component
2. Rename the `extensions/` directory and the `BaseExtension` class to reflect your domain (e.g. `parsers/BaseParser`, `backends/BaseBackend`)
3. In `base.py`, rename the `extension_type` property and add the abstract methods your interface requires
4. In `__init__.py`, update the `PluginRegistry(...)` arguments to match (see the TODO comments)
5. In the Dockerfile, copy the directory to `/app/defaults/<your_dir>/` and copy `registry.py` to `/app/`
6. In the entrypoint, add the directory name to `SUBDIRS`

See `components/data_ingestor/src/parsers/` for a complete example.

## Writing Tests

All components require tests at two levels. The CI pipelines automatically discover test files by name, so following the naming convention is essential.

### Unit tests

Unit tests live in `tests/unit/test_<component_name>.py`. They test your Python logic in isolation — no Docker required. Mock any heavy dependencies (database clients, HTTP calls, model loading).

```bash
./run_tests.sh unit <component_name>
```

### Component tests

Component tests live in `tests/components/test_<component_name>.py`. They build and start the actual Docker container, then verify it behaves correctly over the network. They use the `component_endpoint` pytest fixture, which handles build, start, and teardown automatically.

The fixture is parametrised with a `(service_name, internal_port)` tuple — see the existing component tests under `tests/components/` for the pattern.

```bash
./run_tests.sh component <component_name>
```

At minimum, component tests should verify:
- The health endpoint returns HTTP 200 (if applicable)
- The primary API or function works correctly end-to-end
- Error cases return appropriate responses

---

## Pull Request Checklist

- [ ] `components/<name>/Dockerfile` exists and builds successfully
- [ ] `components/<name>/entrypoint.sh` exists and is executable
- [ ] `components/<name>/src/requirements.txt` lists all Python dependencies
- [ ] Component is added to the root `docker-compose.yaml` with resource limits
- [ ] `tests/unit/test_<name>.py` exists and passes (`./run_tests.sh unit <name>`)
- [ ] `tests/components/test_<name>.py` exists and passes (`./run_tests.sh component <name>`)
- [ ] `components/<name>/README.md` documents usage, configuration, and volume mounts
- [ ] All GitHub Actions pass on the PR
