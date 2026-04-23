# Data Extractor

LLM-based structured field extraction tool. Reads a parquet or CSV file, extracts defined fields from a text column via Ollama, and writes results to the format specified in `runtime_config.json`.

## Role in the pipeline

```
[pii_cleanse]  →  *_cleansed.parquet
                        ↓
                  [data_extractor]  →  *_extracted.csv
```

The typical input is the cleansed parquet produced by `pii_cleanse`. The extractor reads from the `masked_text` column by default. Columns containing unredacted data (e.g. `incident_text`, `ner_labels`) are dropped from the output as defined in the config.

### Skipping PII cleansing

`data_extractor` also accepts a raw `.csv` file directly, allowing `pii_cleanse` to be bypassed entirely. This is useful when you are confident that your data contains no personal or sensitive information and want to go straight to field extraction.

To use this mode, update `source_col` in your `runtime_config.json` to match the text column in your CSV (e.g. `incident_text` instead of the default `masked_text`), then pass the CSV as the input file.

> **Warning:** This is the user's responsibility. If the input data contains personal or sensitive information, skipping `pii_cleanse` means that data will be sent to the LLM and may appear in the extracted output. Only bypass PII cleansing when you are confident the data does not contain sensitive information.

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
python extract.py <input_file> [options]
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `input_file` | required | Path to input file (`.parquet` or `.csv`) |
| `-m`, `--model` | `mistral-small:24b` | Ollama model name |
| `-c`, `--config` | `configs/fields_config.json` | Path to extraction config JSON |
| `-r`, `--runtime-config` | `configs/runtime_config.json` | Path to runtime config |
| `-o`, `--output` | derived from input filename | Override output file path |
| `-n`, `--preview N` | — | Process only the first N rows |

### Examples

```bash
# Full run from cleansed parquet — output format driven by runtime_config.json
python extract.py /data/incidents_cleansed.parquet

# Full run directly from CSV (skipping pii_cleanse — use only when data contains no PII)
# Set source_col in configs/runtime_config.json to match the text column in your CSV first
python extract.py /data/incidents.csv

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
# Full run from cleansed parquet (output format set in runtime_config.json)
docker run --rm -v "$DATA_DIR:/data" extracta-data-extractor /data/incidents_cleansed.parquet

# Full run directly from CSV (skipping pii_cleanse — use only when data contains no PII)
# Set source_col in configs/runtime_config.json to match the text column in your CSV, then rebuild
docker run --rm -v "$DATA_DIR:/data" extracta-data-extractor /data/incidents.csv

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
