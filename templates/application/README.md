# APPLICATION_NAME  <!-- TODO: replace with your application's display name -->

<!-- TODO: Write a one- or two-sentence summary of what the application does and
     which components it combines. -->

<!-- TODO: Optionally add an ASCII diagram showing how the components connect,
     e.g.:

```
┌──────────────────┐     ┌─────────────────┐
│  component_one   │────▶│  component_two  │
│                  │     │                 │
└──────────────────┘     └─────────────────┘
                                │
                          ┌─────┴─────┐
                          │   :PORT   │
                          └───────────┘
```
-->

## Components

<!-- TODO: List the components this application uses. -->

| Component | Description |
|-----------|-------------|
| [COMPONENT_NAME](/components/COMPONENT_NAME/README.md) | <!-- TODO: brief description --> |

## Features

<!-- TODO: Bullet-point list of what the application provides to the user. -->

- TODO

## Prerequisites

Docker and Docker Compose are required. See the [Prerequisites guide](../../docs/prerequisites.md) for installation instructions.

## Usage

Copy [`docker-compose.yaml`](docker-compose.yaml) into the directory where you wish to run the application, then run all commands from that directory.

<!-- TODO: Add step-by-step instructions for starting and using the application.
     Break this into logical subsections (e.g. "Start the database", "Ingest content",
     "Query the API"). Include concrete shell commands for every step. -->

### Start the Application

```bash
docker compose up -d
```

<!-- TODO: Add further subsections as needed, e.g.:

### Ingest Content

```bash
docker compose run COMPONENT_NAME <args>
```

### Query the API

```bash
curl http://localhost:PORT/endpoint
```
-->

### Stop the Application

```bash
docker compose down
```

## Ports

<!-- TODO: List every port the application exposes. -->

| Port | Protocol | Description |
|------|----------|-------------|
| PORT | HTTP | <!-- TODO: description --> |

## Configuration

<!-- TODO: List the config paths that users are likely to customise.
     These will be under the code/ directory created on first run. -->

Configuration files are written to the `code/` directory on first run:

| Path | Description |
|------|-------------|
| `code/COMPONENT_NAME/config/` | <!-- TODO: description --> |

### Customisation

<!-- TODO: Describe how users can customise the application — which config files
     to edit, what extension points exist, and how to apply changes. -->

Each component writes default configuration and code into its `code/` subdirectory on first run. Edit those files or add new ones — changes take effect on the next container restart.

## Resource Limits

<!-- TODO: Fill in the resource limits that match your docker-compose.yaml. -->

| Service | Memory Limit | CPU Limit |
|---------|--------------|-----------|
| COMPONENT_NAME | 2GB | 1 core |
