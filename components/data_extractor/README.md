# Data Extractor

LLM-based structured field extraction tool. Reads a PII-cleansed parquet file (upstream output of `pii_cleanse`), extracts defined fields from the masked text via Ollama, and writes results to the format specified in `runtime_config.json`.

## Role in the pipeline

```
[pii_cleanse]  →  *_cleansed.parquet
                        ↓
                  [data_extractor]  →  *_extracted.csv
```

The input **must** be the cleansed parquet produced by `pii_cleanse/cleanse.py`. The extractor reads from the `masked_text` column by default — never from the original unredacted text. Columns containing unredacted data (e.g. `incident_text`, `ner_labels`) are dropped from the output as defined in the config.

## Configuration

### Extraction config (`configs/fields_config.json`)

Field extraction is entirely config-driven. The default is `configs/fields_config.json`.

```json
{
  "drop_columns": ["incident_text", "ner_labels"],
  "fields_to_extract": [
    {
      "name": "issue",
      "description": "The primary issue described..."
    },
    {
      "name": "severity_indicator",
      "description": "Classify as: 1 - Critical, 2 - High, 3 - Moderate, 4 - Low, 5 - Information"
    }
  ]
}
```

| Key | Description |
|---|---|
| `drop_columns` | Columns to exclude from output — prevents unredacted text from appearing in results. |
| `fields_to_extract` | List of `name` + `description` pairs. The description is passed directly to the LLM. |

### Runtime config (`configs/runtime_config.json`)

Operational settings that are typically set once per deployment:

```json
{
  "ollama_timeout_seconds": 120,
  "output_format": "csv",
  "source_col": "masked_text"
}
```

| Key | Description | Valid values |
|---|---|---|
| `ollama_timeout_seconds` | HTTP client timeout for Ollama requests | Integer (seconds) |
| `output_format` | How extracted output is written | `csv` (default), `json`, `stdout` |
| `source_col` | Column name containing the masked text to extract from | String |

`stdout` is useful for quickly eyeballing model output without writing a file — combine with `-n` to limit rows.

## CLI Usage

```
python extract.py <parquet_path> [options]
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `parquet_path` | required | Path to input parquet (output of `pii_cleanse`) |
| `-m`, `--model` | `mistral-small:24b` | Ollama model name |
| `-c`, `--config` | `configs/fields_config.json` | Path to extraction config JSON |
| `-r`, `--runtime-config` | `configs/runtime_config.json` | Path to runtime config |
| `-o`, `--output` | derived from input filename | Override output file path |
| `-n`, `--preview N` | — | Process only the first N rows |

### Examples

```bash
# Full run — output format driven by runtime_config.json
python extract.py /data/incidents_cleansed.parquet

# Preview 5 rows to terminal (set output_format: stdout in runtime_config.json)
python extract.py /data/incidents_cleansed.parquet -n 5

# Specific model, explicit output path
python extract.py /data/incidents_cleansed.parquet -m qwen2.5:32b -o /data/extracted.csv

# Custom config (different domain)
python extract.py /data/procurement_cleansed.parquet -c configs/procurement_config.json
```

## Output

Output format is controlled by `output_format` in `runtime_config.json`:

- **`csv`** (default) — writes a CSV file alongside the input; human-readable and suitable for review in Excel / BI tools
- **`json`** — writes a JSON array of objects alongside the input
- **`stdout`** — prints each extracted record as formatted JSON to the terminal; no file written

Each record contains all original parquet columns (minus `drop_columns`) plus one key per extracted field. On error for a row, extracted fields are set to `null` and processing continues.

## Docker

Set your data directory once, then reuse across commands:

```bash
export DATA_DIR=/path/to/your/data
```

Build from the Extracta project root:

```bash
docker build -t extracta-data-extractor components/data_extractor
```

Run:

```bash
# Full run (output format set in runtime_config.json)
docker run --rm -v "$DATA_DIR:/data" extracta-data-extractor /data/incidents_cleansed.parquet

# Preview first 5 rows to terminal
docker run --rm -v "$DATA_DIR:/data" extracta-data-extractor /data/incidents_cleansed.parquet -n 5

# Specific model, explicit output
docker run --rm -v "$DATA_DIR:/data" extracta-data-extractor /data/incidents_cleansed.parquet -m qwen2.5:32b -o /data/extracted.csv
```

**Custom config** (override the baked-in default):

```bash
docker run --rm -v "$DATA_DIR:/data" -e EXTRACT_CONFIG=/data/my_config.json extracta-data-extractor /data/cleansed.parquet
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama endpoint. `host.docker.internal` resolves to the host machine on Mac. |
| `EXTRACT_CONFIG` | `/app/configs/fields_config.json` | Path to extraction config inside the container. Override to use a config from the mounted volume. |
| `RUNTIME_CONFIG` | `/app/configs/runtime_config.json` | Path to runtime config inside the container. |

## Dependencies

```
pandas
pyarrow
requests
python-dotenv
tqdm
```
