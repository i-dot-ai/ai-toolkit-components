# AI Toolkit Components Repository

Build AI-powered applications faster with ready-to-use, containerised building blocks.

Use it to build things like: a semantic search tool over your documents, an AI agent that can query your knowledge base via MCP, or a document ingestion pipeline — without wiring up a vector database, embedding models, or an MCP server from scratch.

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
│  │    └─────────────────┘          └────────┬────────┘               │  │
│  │         COMPONENT                  COMPONENT │                    │  │
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

**Components** are standalone Docker services that do one thing well — like storing vectors or parsing documents. They're designed to be mixed and matched.

**Applications** are complete solutions that combine components using docker-compose. Copy an application's `docker-compose.yaml` to your project and you're ready to go.

## Getting Started

Choose your path:

| I want to... | Go to... |
|--------------|----------|
| **Use/adapt an existing application** | [User Guide → Applications](#applications) |
| **Use/adapt individual components** | [User Guide → Components](#components) |
| **Build new components or applications** | [Development Guide](#development-guide) |
| **Contribute back to the community** | [Contributing](docs/contributing.md) |

## Prerequisites

All paths — running an application, using individual components, or developing new ones — require Docker and Docker Compose. See the [Prerequisites guide](docs/prerequisites.md) for installation instructions for macOS, Windows, and Linux.

---

## User Guide

### Applications

Applications are complete, ready-to-run solutions. Each one is a `docker-compose.yaml` that pulls published component images from GHCR, wires them together, and mounts a local `code/` directory where the components write their default configuration and extensibility code on first run. You do not need to clone this repository or touch any source code — copy the `docker-compose.yaml` to your project and customise the files that appear in `code/` after the first run.

The following applications are available:

| Application | Description |
|-------------|-------------|
| [mcp_datastore](applications/mcp_datastore/) | Document ingestion and semantic search with MCP agent access |

To get started, navigate to the application's directory or copy its `docker-compose.yaml` to your project. Each application's README documents the services it includes, how to start them, and how to customise each component.

Ensure you have Docker and Docker Compose installed (see the [Prerequisites guide](docs/prerequisites.md)). You can then run the application by executing the following command in the terminal from the application's directory:

```bash
docker compose up -d
```

This will initiate the process of pulling the necessary images and starting the services defined in the `docker-compose.yaml` file. When the containers run, they will write customisable code into the mounted volumes, allowing you to modify and extend the functionality as needed. For example:

```bash
$ cp applications/mcp_datastore/docker-compose.yaml .
$ docker compose up -d
```

After running the application for the first time, you can explore the `code` directories to see the default configurations and code. Modify these files to tailor the components to your specific use case. See specific component READMEs for examples of how to customise.

### Components

Components are single-purpose Docker services — the building blocks. Each one does one thing well (store vectors, parse and embed documents, serve an MCP interface) and is designed to be combined with others. Components are published as images to GHCR and expose a single volume mount point (`/app/custom`) where their default configuration and extensibility code are copied on first run. You can modify those files, or add new plugins and extension classes, without rebuilding the image.

The following components are available:

| Component | Description |
|-----------|-------------|
| [vector_db](components/vector_db/) | Qdrant vector database with plugin support |
| [data_ingestor](components/data_ingestor/) | Content ingestion and embedding |
| [mcp_server](components/mcp_server/) | MCP server exposing vector DB tools for AI agents |
| [vector_query](components/vector_query/) | CLI for querying and managing vector databases directly |

To use a component directly, reference its published image in your own `docker-compose.yaml` and mount a local directory to `/app/custom`:

```yaml
services:
  vector_db:
    image: ghcr.io/i-dot-ai/ai-toolkit-vector_db:latest
    ports:
      - "6333:6333"
    volumes:
      - ./code/vector_db:/app/custom
```

All components are **continuously running services** that expose an API or CLI interface. Start them as background services with `docker compose up` and stop them with `docker compose down`. For example, to ingest a URL into the data ingestor:

```bash
docker compose exec data_ingestor run http://example.com
```

Components are customisable via mounted volumes. Each component mounts a directory under `code` where defaults are copied on first run. Users can modify these files to customize behaviour. Please refer to each component's README for specific instructions on usage, and how to customize and extend its functionality.


## Development Guide

If you wish to add or develop entirely new components or applications, or build off the source code directly, you can clone the entire repository. The structure is as follows:

```
.
├── applications/               # Application implementations using components
│   ├── <application-a>/        # Example application 1
│   │   ├── docker-compose.yaml # Application-specific service definitions
│   ├── <application-b>/        # Example application 2
├── components/                 # Independent service components
│   └── <component-a>/          # Example component service
│       ├── src/                # Application source code
│       ├── Dockerfile          # Component build definition
│       └── entrypoint.sh       # Container startup script
├── tests/                      # Test infrastructure
│   ├── applications/           # Application integration tests
│   │   └── test_<application-a>.py
│   ├── components/             # Component container tests (require Docker)
│   │   └── test_<component-a>.py
│   ├── unit/                   # Unit tests (no Docker needed)
│   │   └── test_<component-a>.py
│   ├── test_utils.py           # Shared testing utilities
│   └── conftest.py             # Pytest fixtures
├── .github/workflows/          # CI/CD pipeline definitions
├── docker-compose.yaml         # Local dev environment setup
└── LICENSE
```

The `components/` directory contains modular services that can be independently developed, tested, and deployed. The `applications/` directory showcases how these components can be orchestrated to build complete AI solutions.

### Quick Start

1. Ensure Docker and Docker Compose are installed — see the [Prerequisites guide](docs/prerequisites.md) if you haven't set these up yet.

2. **Build and start services**:
   ```bash
   docker compose build <component-a>
   ```

3. **Launch the component**:
   ```bash
   docker compose up -d <component-a>
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```
   This enables automatic security and code quality checks on every `git commit`. Note that the Docker daemon must be running when you commit, as the Trivy hook requires it.

5. **Run tests**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync
   # Individual component tests
   ./run_tests.sh component <component-a>
   # Individual application tests
   ./run_tests.sh application <application-a>
   ```

6. **Customise/add new components**:
   - Create new services by adding `components/<component-new>/Dockerfile` and `entrypoint.sh`
   - Add/modify source code in `components/<component-a>/src/`
   - Add tests for new functionality under `tests/components/`

7. **Customise/add new application templates**:
   - Create new directories under `applications/`
   - Define services in `docker-compose.yaml` files
   - Add application-specific tests under `tests/applications/`


### Testing


#### Run tests locally

```bash
# Run unit tests (no Docker needed)
./run_tests.sh unit

# Run component tests (starts service automatically)
./run_tests.sh component <component-a>

# Run application tests
./run_tests.sh application <application-a>
```

#### Adding new tests

Tests are written using `pytest`. To add new tests:
1. Add unit tests under `tests/unit/` named `test_<component_name>.py`
2. Add component tests under `tests/components/` named `test_<component_name>.py`
3. Add application tests under `tests/applications/` named `test_<application_name>.py`

### CI/CD Pipelines


The CI/CD system runs the following workflows:

#### Testing

1. **Unit Tests** (`.github/workflows/unit-tests.yml`):
   - Triggered on push to main and PRs
   - Dynamically discovers components with unit tests and runs each in a parallel matrix job (no Docker needed)
   - Test results from all components are published as a single combined report

2. **Component Build & Test** (`.github/workflows/component-build-test.yml`):
   - Triggered on push to main and PRs
   - Dynamically discovers components and runs each in a parallel matrix job
   - Each job builds the component's Docker image and runs its container tests
   - Test results from all components are published as a single combined report

3. **Application Test** (`.github/workflows/application-test.yml`):
   - Runs after successful component builds
   - Dynamically discovers applications and runs each in a parallel matrix job
   - Each job builds all component images and tests the full application stack
   - Test results from all applications are published as a single combined report

#### Publishing

4. **Publish Latest Images** (`.github/workflows/publish-latest.yml`):
   - Triggered automatically after a successful "Docker Build and Test" workflow on `main`
   - Builds and pushes `latest`-tagged images for all components to GHCR (`ghcr.io/i-dot-ai/ai-toolkit-<component>`)

5. **Release** (`.github/workflows/release.yml`):
   - Manually triggered via `workflow_dispatch`
   - Accepts a semver version (e.g., `1.2.3`) and an optional component name (defaults to all)
   - Builds and pushes images tagged with both `v<version>` and `latest`
   - Creates a GitHub Release with auto-generated release notes

## Contributing

1. Create feature branches from `main`
2. Include tests for new functionality
3. Verify all GitHub Actions pass
4. Maintain documentation updates

See [Contributing](docs/contributing.md) for a full guide on adding new components, including templates, testing requirements, and the pull request checklist.

See [LICENSE](LICENSE) for terms.
