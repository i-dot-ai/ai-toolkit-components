# Data Extractor

LLM-based structured field extraction tool. Reads a PII-cleansed parquet file (upstream output of `pii_cleanse`), extracts defined fields from the masked text via Ollama, and writes results to JSON.

## Author

**Lawrence Freeman**  
AI Engineer at GBRx  
AI Incubator Accelerator (AIIA)

- GitHub: https://github.com/lawrencefreeman
- LinkedIn: https://www.linkedin.com/in/thedatachef/

## Prerequisites

- [Ollama](https://ollama.com/) installed and running locally with a model pulled, e.g. `ollama pull mistral-small:24b`
- [Docker](https://www.docker.com/)
- A PII-cleansed parquet file produced by `pii_cleanse`

> **Platform note:** The default `OLLAMA_HOST` (`host.docker.internal:11434`) works on Mac and Windows Docker Desktop. On Linux, `host.docker.internal` is not available by default — override it with the host's Docker bridge IP: `-e OLLAMA_HOST=http://172.17.0.1:11434`. On Windows, the recommended setup is to run both Ollama and Docker inside WSL2.

---

## Role in the pipeline

```
[pii_cleanse]  →  *_cleansed.parquet
                        ↓
                  [data_extractor]  →  *_extracted.json
```

The input **must** be the cleansed parquet produced by `pii_cleanse/cleanse.py`. The extractor reads from the `masked_text` column by default — never from the original unredacted text. Columns containing unredacted data (e.g. `incident_text`, `ner_labels`) are dropped from the output as defined in the config.

## Configuration

Field extraction is entirely config-driven via a JSON file. The default is `configs/extracta_config.json`.

### Config structure

```json
{
  "text_column": "masked_text",
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
| `text_column` | Column in the parquet to extract from. Should always be the masked text column. |
| `drop_columns` | Columns to exclude from output — use this to ensure unredacted text is never written to the output JSON. |
| `fields_to_extract` | List of `name` + `description` pairs. The description is passed directly to the LLM as an instruction. |

## CLI Usage

```
python components/data_extractor/src/extract.py <parquet_path> [options]
```

### Arguments

| Argument | Default | Description |
|---|---|---|
| `parquet_path` | required | Path to input parquet (output of `pii_cleanse`) |
| `-m`, `--model` | `mistral-small:24b` | Ollama model name |
| `-c`, `--config` | `configs/extracta_config.json` | Path to extraction config JSON |
| `--text-col` | from config | Override the text column from config |
| `--mode` | `test` | `test`: small sample eyeball; `release`: full dataset |
| `-n`, `--test-rows` | `5` | Number of rows to process in test mode |
| `-o`, `--output` | `<parquet_stem>_extracted.json` | Output JSON path |

### Examples

```bash
# Test mode — 5 rows, default model, prints summary
python components/data_extractor/src/extract.py "applications/extracta/sample_data/synthetic_incidents_100_cleansed.parquet"

# Test mode — 10 rows, specific model
python components/data_extractor/src/extract.py "applications/extracta/sample_data/synthetic_incidents_100_cleansed.parquet" \
  -m qwen2.5:32b -n 10

# Release mode — full dataset
python components/data_extractor/src/extract.py "applications/extracta/sample_data/synthetic_incidents_100_cleansed.parquet" \
  --mode release \
  -o "applications/extracta/sample_data/extracted.json"

# Custom config (different domain)
python components/data_extractor/src/extract.py "dummy data/procurement_cleansed.parquet" \
  -c configs/procurement_config.json \
  --mode release \
  -o "dummy data/procurement_extracted.json"
```

## Output

A JSON array of objects. Each object contains:
- All original parquet columns **except** those listed in `drop_columns`
- One key per extracted field, as defined in `fields_to_extract`

```json
[
  {
    "incident_id": "INC-001",
    "timestamp": "2024-01-15T09:23:00",
    "masked_text": "Signal failure reported at [LOCATION]...",
    "issue": "Signal failure caused by faulty relay",
    "impact": "45 minute delays to 12 services",
    "resolution_action": "Relay replaced by S&T team",
    "severity_indicator": "2"
  }
]
```

On error for a row, extracted fields are set to `null` and processing continues.

## Docker

### Build

Run from the Extracta project root:

```bash
docker build -f components/data_extractor/Dockerfile -t extracta-data-extractor components/data_extractor
```

### Running the container

Mount the directory containing your cleansed parquet and output location to `/data`. Ollama must be running on the host machine.

**Test mode — 5 rows:**
```bash
docker run --rm \
  -v "$(pwd)/applications/extracta/sample_data:/data" \
  data-extractor \
  /data/synthetic_incidents_100_cleansed.parquet
```

**Release mode — full dataset:**
```bash
docker run --rm \
  -v "$(pwd)/applications/extracta/sample_data:/data" \
  data-extractor \
  /data/synthetic_incidents_100_cleansed.parquet \
  --mode release \
  -o /data/extracted.json
```

**Specific model:**
```bash
docker run --rm \
  -v "$(pwd)/applications/extracta/sample_data:/data" \
  data-extractor \
  /data/synthetic_incidents_100_cleansed.parquet \
  -m qwen2.5:32b \
  --mode release \
  -o /data/extracted.json
```

**Custom config** (override the baked-in default):
```bash
docker run --rm \
  -v "$(pwd)/applications/extracta/sample_data:/data" \
  -e EXTRACT_CONFIG=/data/my_config.json \
  data-extractor \
  /data/cleansed.parquet \
  --mode release \
  -o /data/extracted.json
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama endpoint. `host.docker.internal` resolves to the host machine on Mac. |
| `EXTRACT_CONFIG` | `/app/configs/extracta_config.json` | Path to extraction config inside the container. Override to use a config from the mounted volume. |

## Dependencies

```
pandas
pyarrow
requests
python-dotenv
tqdm
```
