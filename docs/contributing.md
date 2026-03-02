# Contributing

This guide explains how to add new components and applications to this repository.

**Components** are standalone Docker services that do one thing well — the building blocks.
**Applications** are docker-compose orchestrations that wire components into complete solutions.

## Prerequisites

See the [Prerequisites guide](prerequisites.md) for full installation instructions. You will need:

- Docker and Docker Compose
- Python 3.12+
- `uv` (the project's package manager)
- Project dependencies installed with `uv sync`

---

## Contribution Guides

- [Adding a New Component](contributing_components.md) — Dockerfile, entrypoint, source code, customisation pattern, plugin patterns, and tests
- [Adding a New Application](contributing_applications.md) — docker-compose setup, README, and tests

You may also wish to extend an existing component by adding new extensions (e.g. a new parser, embedder, or backend). See the [Plugin Patterns](contributing_components.md#plugin-patterns) section of the component guide.

---

## CI/CD Overview

The following workflows run automatically on every pull request:

| Workflow | What it does |
|----------|-------------|
| `unit-tests.yml` | Runs `tests/unit/test_<name>.py` for each component in parallel |
| `component-build-test.yml` | Builds each component's Docker image and runs `tests/components/test_<name>.py` |
| `application-test.yml` | Runs `tests/applications/test_<name>.py` for each application after component builds succeed |

On merge to `main`, a `publish-latest.yml` workflow automatically pushes a `latest`-tagged image to GHCR (`ghcr.io/i-dot-ai/ai-toolkit-<component_name>`). Versioned releases are created manually via the `release.yml` workflow.

The CI pipelines discover components and tests automatically by scanning directory and file names — no pipeline configuration changes are needed.
