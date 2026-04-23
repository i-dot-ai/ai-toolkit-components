# Extracta

Three-stage pipeline for LLM-based PII redaction and structured field extraction from free-text records. All stages run locally via [Ollama](https://ollama.com/) and are containerised with Docker.

---

## Architecture

![Extracta pipeline architecture](extracta_architecture.drawio.png)

`pii_eval` is an offline evaluation step — it does not sit in the production path. Run it to validate model/config choices before committing to `pii_cleanse`.

---

## Repository structure

```
components/
  pii_eval/          LLM PII masking evaluator (optional, offline)
  pii_cleanse/       PII redaction — produces cleansed parquet
  data_extractor/    Structured field extraction from cleansed text

applications/
  extracta/          Docker Compose orchestration of all three components

tests/
  unit/              Unit tests (no Docker required)
  components/        Container-level tests for each component
  applications/      Integration tests for the full pipeline

configs/             Shared default config files (also baked into each component image)
dummy data/          Synthetic UK rail incident logs for local testing
```

---

## Components

| Component | Directory | README |
|---|---|---|
| LLM PII evaluator *(optional)* | `components/pii_eval/` | [components/pii_eval/README.md](components/pii_eval/README.md) |
| PII redaction | `components/pii_cleanse/` | [components/pii_cleanse/README.md](components/pii_cleanse/README.md) |
| Structured field extraction | `components/data_extractor/` | [components/data_extractor/README.md](components/data_extractor/README.md) |

---

## Quick start

See [applications/extracta/README.md](applications/extracta/README.md) for Docker Compose usage running the full pipeline.

### Prerequisites

- [Ollama](https://ollama.com/) installed and running locally
- [Docker](https://www.docker.com/) and Docker Compose
- A model pulled locally, e.g.:
  ```bash
  ollama pull mistral-small:24b
  ```

### Building component images

Each component has its own Dockerfile, built from its own directory:

```bash
docker build -t extracta-pii-cleanse   components/pii_cleanse
docker build -t extracta-data-extractor components/data_extractor
docker build -t extracta-pii-eval      components/pii_eval
```

---

## Configuration

| File | Used by | Purpose |
|---|---|---|
| `configs/sensitive_attr_config.json` | `pii_eval`, `pii_cleanse` | PII entity actions (`redact` / `ignore`) |
| `configs/fields_config.json` | `data_extractor` | Fields to extract from masked text |

Default configs are baked into each component image. Override at runtime by mounting a custom config and setting the relevant environment variable (`SENSITIVE_CONFIG` or `EXTRACT_CONFIG`).

---

## Environment variables

All three containers respect:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama endpoint. `host.docker.internal` resolves to the host on Mac. Override for Linux or remote Ollama. |

`pii_eval` additionally requires:

| Variable | Description |
|---|---|
| `HF_TOKEN` | Hugging Face token for the labelled evaluation dataset. Pass via `--env-file .env`. Not required when using a local dataset. |

`.env` file format — values must be **unquoted**:

```
HF_TOKEN=hf_yourtoken
```

---

## Data flow

- `pii_cleanse` outputs a parquet with a `masked_text` column — the only text column `data_extractor` reads.
- `data_extractor` drops original unredacted text columns from its output — these are never written to the extracted JSON.
- All stages mount data via `-v /path/to/data:/data`. Input and output paths inside the container are under `/data`.

---

## Development

### Installing test dependencies

Test dependencies are declared as an optional extra in `pyproject.toml` and are kept separate from the runtime dependencies baked into each component's Docker image.

Install them using `uv` (recommended):

```bash
uv sync --extra test
```

Or with pip:

```bash
pip install -e ".[test]"
```

### Running the unit tests

Unit tests require no Docker, no Ollama, and no network access — all LLM calls are mocked.

```bash
pytest tests/unit/ -v
```

### Test structure

| Directory | What it tests | Requires |
|---|---|---|
| `tests/unit/` | Pure logic — prompt building, tokenisation, metrics | Nothing external |
| `tests/components/` | Each component's Docker image end-to-end | Docker |
| `tests/applications/` | Full pipeline via Docker Compose | Docker + Ollama |

---

## Licence

MIT — see [LICENSE](LICENSE).
