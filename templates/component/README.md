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

The custom directory contains:
- `config/` - Configuration files

## Configuration

### Config File

Defaults are copied to `/app/custom/config/` on first run.

```yaml
# Example settings
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SOME_VAR` | What it does | `default_value` |

## Ports

| Port | Protocol | Description |
|------|----------|-------------|
| `8080` | HTTP | REST API |
