# Contributing: Adding a New Application

Applications are docker-compose orchestrations that wire existing components into a complete, ready-to-use solution. They live in `applications/<name>/` and contain no component source code of their own.

## Prerequisites

See the [Prerequisites guide](prerequisites.md) for full installation instructions. You will need:

- Docker and Docker Compose
- Python 3.12+
- `uv` (the project's package manager)
- Project dependencies installed with `uv sync`

---

## Templates

Ready-to-use starting-point files are provided in `templates/application/`:

| File | Purpose |
|------|---------|
| [`templates/application/docker-compose.yaml`](../templates/application/docker-compose.yaml) | Annotated docker-compose file covering the full application pattern |
| [`templates/application/README.md`](../templates/application/README.md) | README template with all required sections |

Copy these into your new application directory and replace the `APPLICATION_NAME` and `COMPONENT_NAME` placeholders.

## Structure

```
applications/<application_name>/
├── docker-compose.yaml   # Service definitions
└── README.md             # Usage and configuration guide
```

## Writing the docker-compose.yaml

Start from the template at [`templates/application/docker-compose.yaml`](../templates/application/docker-compose.yaml). Copy it to `applications/<application_name>/docker-compose.yaml` and work through the TODO comments.

Key conventions:
- Pull published GHCR images (`ghcr.io/i-dot-ai/ai-toolkit-<component_name>:latest`) rather than building locally — applications consume components, not source
- Mount `./code/<component_name>` to `/app/custom` for each service — this is where default configs and customisable code are written on first run
- Always set resource limits
- Use `depends_on` with `condition: service_healthy` for services that must start in order
- Pass connection details (hostnames, ports) as environment variables, not in config files
- See `applications/mcp_datastore/docker-compose.yaml` for a complete example

## Writing the README

Start from the template at [`templates/application/README.md`](../templates/application/README.md). Document everything a user needs to run the application without reading any other files: prerequisites, how to start each service, how to ingest or query data, ports, configuration paths, and resource limits. See `applications/mcp_datastore/README.md` for a completed example.

## Writing Tests

Application tests live in `tests/applications/test_<application_name>.py`. They use the `application_endpoint` fixture, which copies the `docker-compose.yaml` to a temporary directory, starts all services, and tears them down after the test run.

```bash
./run_tests.sh application <application_name>
```

At minimum, application tests should verify:
- All services reach a healthy state
- The core end-to-end flow works (e.g. ingest content, then query it)
- Default customisation directories are created and populated on first run

See `tests/applications/test_mcp_datastore.py` for a complete example.

---

## Pull Request Checklist

- [ ] `applications/<name>/docker-compose.yaml` uses GHCR images and mounts `./code/<component>/` volumes
- [ ] Resource limits are set for every service
- [ ] `tests/applications/test_<name>.py` exists and passes (`./run_tests.sh application <name>`)
- [ ] `applications/<name>/README.md` covers prerequisites, usage, ports, and configuration
- [ ] All GitHub Actions pass on the PR
