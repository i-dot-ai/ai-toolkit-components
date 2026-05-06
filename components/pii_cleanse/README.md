# Personal Identifiable Information (PII) Cleaner Tool

LLM-based PII masking tool. Applies configurable redaction rules to a CSV of free-text records, producing a cleansed output file for downstream field extraction.

## Role in the pipeline

This component sits **upstream** of the data extraction step. Before running `pii_cleanse` in production, periodic evaluation should be performed using `pii_eval/evaluate.py` to compare PII masking performance across open-weight models. Evaluation results are appended to a CSV for cross-model comparison, allowing the best model to be selected.

Based on evaluation against the [ai4privacy](https://huggingface.co/datasets/ai4privacy/open-pii-masking-500k-ai4privacy) benchmark dataset, **`mistral-small:24b` performed best for local inference via Ollama** and is therefore the default model.

```
[evaluate.py]  ←  periodic model benchmarking
      ↓
  pick best model
      ↓
[cleanse.py]   →  cleansed .parquet
      ↓
[data_extractor/extract.py]
```

## How it works

The tool builds a system prompt directly from `sensitive_attr_config.json`, instructing the LLM to apply per-entity redaction rules to each row of free text. No NLP libraries (Presidio, spaCy) are used — the LLM does all the work.

Two actions are supported in the config:
- `"redact"` — replace the entity with `[LABEL]` (e.g. `[PERSON]`, `[EMAIL]`)
- `"ignore"` — leave the value unchanged

Any value other than `"ignore"` is treated as `"redact"`, so the existing config format remains compatible.

### Example config (`configs/sensitive_attr_config.json`)

```json
{
    "PERSON": "redact",
    "EMAIL": "redact",
    "PHONE": "redact",
    "LOCATION": "ignore",
    "DATE": "ignore",
    "TIME": "ignore",
    "ID": "mask"
}
```

### Runtime config (`configs/runtime_config.json`)

Operational settings that are typically set once per deployment and do not change between runs:

```json
{
  "ollama_timeout_seconds": 120,
  "output_format": "parquet",
  "source_col": "incident_text",
  "output_col": "masked_text"
}
```

| Key | Description | Valid values |
|---|---|---|
| `ollama_timeout_seconds` | HTTP client timeout for Ollama requests | Integer (seconds) |
| `output_format` | How cleansed output is written | `parquet` (default), `csv`, `stdout` |
| `source_col` | Column name containing the raw free text | String |
| `output_col` | Column name for the masked text in the output | String |

`stdout` is useful for quickly eyeballing model output without writing a file — combine with `-n` to limit rows.

## Usage

```
python cleanse.py <model> <csv_path> [options]
```

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `model` | yes | — | Model name, e.g. `mistral-small:24b` or `gpt-4o` |
| `csv_path` | yes | — | Path to input CSV file |
| `-p, --provider` | no | `ollama` | Inference provider: `ollama` or `openai` |
| `-c, --sensitive-config` | no | `configs/sensitive_attr_config.json` | Path to PII label/action config |
| `-r, --runtime-config` | no | `configs/runtime_config.json` | Path to runtime config |
| `-o, --output` | no | `<csv_stem>_cleansed.<ext>` | Override output file path |
| `-n, --preview N` | no | — | Process only the first N rows |

### Examples

```bash
# Full run — output format and columns driven by runtime_config.json
python cleanse.py mistral-small:24b /data/incidents.csv

# Preview 5 rows to terminal (set output_format: stdout in runtime_config.json)
python cleanse.py mistral-small:24b /data/incidents.csv -n 5

# Explicit output path
python cleanse.py mistral-small:24b /data/incidents.csv -o /data/incidents_cleansed.parquet

# OpenAI provider
python cleanse.py gpt-4o /data/incidents.csv -p openai
```

## Output

Output format is controlled by `output_format` in `runtime_config.json`:

- **`parquet`** (default) — writes a parquet file alongside the input; expected input format for `data_extractor`
- **`csv`** — writes a CSV file alongside the input
- **`stdout`** — prints source and masked text for each row to the terminal; no file written

## Docker

Set your data directory once, then reuse across commands:

```bash
export DATA_DIR=/path/to/your/data
```

Build from the Extracta project root:

```bash
docker build -t extracta-pii-cleanse components/pii_cleanse
```

Run:

```bash
# Full run (output format set in runtime_config.json)
docker run --rm -v "$DATA_DIR:/data" extracta-pii-cleanse mistral-small:24b /data/incidents.csv

# Preview first 5 rows to terminal
docker run --rm -v "$DATA_DIR:/data" extracta-pii-cleanse mistral-small:24b /data/incidents.csv -n 5

# Explicit output path
docker run --rm -v "$DATA_DIR:/data" extracta-pii-cleanse mistral-small:24b /data/incidents.csv -o /data/incidents_cleansed.parquet
```

Override the Ollama host if needed:

```bash
docker run --rm -e OLLAMA_HOST=http://host.docker.internal:11434 -v "$DATA_DIR:/data" extracta-pii-cleanse mistral-small:24b /data/incidents.csv
```

## Dependencies

Minimal — no NLP libraries required:

```
pandas
pyarrow
requests
python-dotenv
openai
tqdm
```
