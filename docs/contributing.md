# Contributing

This guide explains how to add new components and applications to this repository.

**Components** are standalone Docker services that do one thing well — the building blocks.
**Applications** are docker-compose orchestrations that wire components into complete solutions.

## Prerequisites

See the [Development guide](development.md) for environment setup instructions. You will need Docker, Docker Compose, Python 3.12+, and `uv`.

---

## Contribution Guides

- [Adding a New Component](contributing_components.md) — Dockerfile, entrypoint, source code, customisation pattern, plugin patterns, and tests
- [Adding a New Application](contributing_applications.md) — docker-compose setup, README, and tests

You may also wish to extend an existing component by adding new extensions (e.g. a new parser, embedder, or backend). See the [Plugin Patterns](contributing_components.md#plugin-patterns) section of the component guide.

---

## CI/CD

The CI/CD workflows run automatically on every pull request. See the [Development guide](development.md#cicd-pipelines) for a full description of each workflow.

The short version: push your branch, open a PR, and the pipelines will build your component, run all tests, and report results. No pipeline configuration changes are needed — components and applications are discovered automatically.

On merge to `main`, a `publish-latest.yml` workflow automatically pushes a `latest`-tagged image to GHCR (`ghcr.io/i-dot-ai/ai-toolkit-<component_name>`).
