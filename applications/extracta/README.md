# Extracta Application

Docker Compose orchestration of the three Extracta components into a complete PII-redaction and field-extraction pipeline.

## Components

| Service | Component | Purpose |
|---|---|---|
| `pii_eval` | `components/pii_eval` | Optional: benchmark LLM PII masking against ground truth |
| `pii_cleanse` | `components/pii_cleanse` | Redact PII from free-text CSV records |
| `data_extractor` | `components/data_extractor` | Extract structured fields from cleansed parquet |

`pii_eval` is an offline evaluation step — it does not sit in the production path. Run it to validate model/config choices before committing to `pii_cleanse`.

## Prerequisites

- [Ollama](https://ollama.com/) installed and running locally with your chosen model pulled, e.g.:
  ```bash
  ollama pull mistral-small:24b
  ```
- Docker and Docker Compose

## Usage

Each stage is run independently using Docker Compose profiles. Mount your data directory via the `DATA_DIR` environment variable (defaults to `./data`).

### Step 1 (optional): Evaluate a model's PII masking

```bash
DATA_DIR=/path/to/data docker compose --profile eval run --rm pii_eval \
  mistral-small:24b -n 100 -o /data/eval_results.csv
```

### Step 2: Redact PII from your CSV

```bash
DATA_DIR=/path/to/data docker compose --profile cleanse run --rm pii_cleanse \
  mistral-small:24b /data/incidents.csv \
  --source-col incident_text \
  --mode release \
  -o /data/incidents_cleansed.parquet
```

### Step 3: Extract structured fields

```bash
DATA_DIR=/path/to/data docker compose --profile extract run --rm data_extractor \
  /data/incidents_cleansed.parquet \
  --mode release \
  -o /data/incidents_extracted.json
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama endpoint. `host.docker.internal` resolves to the host on Mac. Override for Linux or remote Ollama. |
| `DATA_DIR` | `./data` | Host directory mounted to `/data` inside each container. |

For `pii_eval` with the HuggingFace dataset, pass `HF_TOKEN` at runtime:

```bash
DATA_DIR=/path/to/data HF_TOKEN=hf_yourtoken docker compose --profile eval run --rm pii_eval \
  mistral-small:24b -o /data/eval_results.csv
```

## Configuration

Default configs are baked into each component image. To override, mount a custom config and point to it via environment variable:

| Variable | Component | Description |
|---|---|---|
| `SENSITIVE_CONFIG` | `pii_cleanse` | Path to PII entity/action config JSON |
| `EXTRACT_CONFIG` | `data_extractor` | Path to field extraction config JSON |

Example with a custom config mounted from the data directory:

```bash
DATA_DIR=/path/to/data EXTRACT_CONFIG=/data/my_config.json \
  docker compose --profile extract run --rm data_extractor \
  /data/incidents_cleansed.parquet --mode release -o /data/extracted.json
```
