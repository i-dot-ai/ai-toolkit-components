# Development Guide

This guide covers setting up the repository for local development: cloning, building components, running tests, and understanding the CI/CD pipelines.

If you want to contribute a new component or application, see the [Contributing guide](contributing.md) once you have your environment set up.

## Prerequisites

See the [Prerequisites guide](prerequisites.md) for full installation instructions. You will need:

- Docker and Docker Compose
- Python 3.12+
- `uv` (the project's package manager)

## Repository Structure

```
.
├── applications/               # Application implementations using components
│   └── <application-name>/
│       ├── docker-compose.yaml # Application-specific service definitions
│       └── README.md
├── components/                 # Independent service components
│   └── <component-name>/
│       ├── src/                # Application source code
│       ├── Dockerfile          # Component build definition
│       ├── entrypoint.sh       # Container startup script
│       └── README.md
├── docs/                       # Documentation
├── templates/                  # Starting-point files for new components and applications
├── tests/                      # Pytest-based test suite
│   ├── applications/           # Application integration tests
│   ├── components/             # Component container tests (require Docker)
│   ├── unit/                   # Unit tests (no Docker needed)
│   ├── conftest.py             # Pytest fixtures
│   └── test_utils.py           # Shared testing utilities
├── .github/workflows/          # CI/CD pipeline definitions
└── docker-compose.yaml         # Local dev environment setup
```

## Quick Start

1. Clone the repository:
   ```bash
   git clone git@github.com:i-dot-ai/ai-toolkit-components.git
   cd ai-toolkit-components
   ```

2. Install Python dependencies:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   uv sync
   ```

3. Build a component:
   ```bash
   docker compose build <component-name>
   ```

4. Start a component:
   ```bash
   docker compose up -d <component-name>
   ```

5. Run its tests:
   ```bash
   ./run_tests.sh component <component-name>
   ```

## Testing

### Running tests locally

```bash
# Unit tests — no Docker needed
./run_tests.sh unit

# Unit tests for a specific component
./run_tests.sh unit <component-name>

# Component tests — builds and starts the component automatically
./run_tests.sh component <component-name>

# Application tests
./run_tests.sh application <application-name>

# Run directly with pytest
uv run pytest -v tests/unit/
uv run pytest -v tests/components/test_<component-name>.py
```

### Test naming conventions

| Test type | Location | File name |
|-----------|----------|-----------|
| Unit tests | `tests/unit/` | `test_<component_name>.py` |
| Component tests | `tests/components/` | `test_<component_name>.py` |
| Application tests | `tests/applications/` | `test_<application_name>.py` |

Tests are written using `pytest`. The `component_endpoint` fixture in `tests/conftest.py` handles building, starting, and cleaning up Docker services automatically for component and application tests.

## CI/CD Pipelines

The following workflows run automatically on every pull request and push to `main`.

### Testing

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `unit-tests.yml` | Push to main, PRs | Discovers components with unit tests and runs each in a parallel matrix job |
| `component-build-test.yml` | Push to main, PRs | Builds each component's Docker image and runs its container tests in parallel |
| `application-test.yml` | After component builds succeed | Builds all component images and tests each application stack in parallel |

All workflows discover components and applications automatically by scanning directory and file names — no pipeline configuration changes are needed when adding new components.

### Publishing

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `publish-latest.yml` | Merge to main (after tests pass) | Builds and pushes `latest`-tagged images to GHCR (`ghcr.io/i-dot-ai/ai-toolkit-<component>`) |
| `release.yml` | Manual (`workflow_dispatch`) | Accepts a semver version and optional component name; builds and pushes `v<version>` + `latest` tags; creates a GitHub Release |
