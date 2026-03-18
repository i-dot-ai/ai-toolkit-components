# Personal Indentifiable Information (PII) Cleaner Tool

LLM-based PII masking tool. Applies configurable redaction rules to a CSV of free-text records, producing a cleansed parquet file for downstream field extraction.

## Author

**Lawrence Freeman**  
AI Engineer at GBRx  
AI Incubator Accelerator (AIIA)

- GitHub: https://github.com/lawrencefreeman
- LinkedIn: https://www.linkedin.com/in/thedatachef/

## Prerequisites

- [Ollama](https://ollama.com/) installed and running locally with a model pulled, e.g. `ollama pull mistral-small:24b`
- [Docker](https://www.docker.com/)

> **Platform note:** The default `OLLAMA_HOST` (`host.docker.internal:11434`) works on Mac and Windows Docker Desktop. On Linux, `host.docker.internal` is not available by default — override it with the host's Docker bridge IP: `-e OLLAMA_HOST=http://172.17.0.1:11434`. On Windows, the recommended setup is to run both Ollama and Docker inside WSL2.

---

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

This produces the following system prompt at runtime:

```
You are a PII detection assistant. Apply the following rules to the text:
- PERSON: replace with [PERSON]
- EMAIL: replace with [EMAIL]
- PHONE: replace with [PHONE]
- LOCATION: leave unchanged
- DATE: leave unchanged
- TIME: leave unchanged
- ID: replace with [ID]
Return ONLY the modified text with no explanation or commentary.
```

## Usage

```
python components/pii_cleanse/src/cleanse.py <model> <csv_path> [options]
```

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `model` | yes | — | Model name, e.g. `mistral-small:24b` or `gpt-4o` |
| `csv_path` | yes | — | Path to input CSV file |
| `-p, --provider` | no | `ollama` | Inference provider: `ollama` or `openai` |
| `-c, --sensitive-config` | no | `configs/sensitive_attr_config.json` | Path to PII label/action config |
| `--source-col` | no | `source_text` | Name of the source text column in the CSV |
| `--output-col` | no | `masked_text` | Column name for the masked text in the output |
| `--mode` | no | `test` | `test` — small sample eyeball; `release` — full dataset |
| `-n, --test-rows` | no | `5` | Number of rows to process in test mode |
| `--test-output` | no | off | In test mode, write to `test_output.csv` instead of printing |
| `-o, --output` | no | `<csv_stem>_cleansed.parquet` | Output path for release mode parquet |

### Examples

```bash
# Test mode — print 5 rows to terminal (default)
python components/pii_cleanse/src/cleanse.py mistral-small:24b "applications/extracta/sample_data/synthetic_incidents_100.csv" --source-col incident_text

# Test mode — write to test_output.csv, 10 rows
python components/pii_cleanse/src/cleanse.py mistral-small:24b "applications/extracta/sample_data/synthetic_incidents_100.csv" --source-col incident_text -n 10 --test-output

# Release mode — full dataset, auto-named parquet output
python components/pii_cleanse/src/cleanse.py mistral-small:24b "applications/extracta/sample_data/synthetic_incidents_100.csv" --source-col incident_text --mode release

# Release mode — explicit output path
python components/pii_cleanse/src/cleanse.py mistral-small:24b "applications/extracta/sample_data/synthetic_incidents_100.csv" --source-col incident_text --mode release -o "applications/extracta/sample_data/synthetic_incidents_100_cleansed.parquet"

# OpenAI provider
python components/pii_cleanse/src/cleanse.py gpt-4o "applications/extracta/sample_data/synthetic_incidents_100.csv" --source-col incident_text -p openai --mode release

# Custom sensitive config
python components/pii_cleanse/src/cleanse.py mistral-small:24b "applications/extracta/sample_data/synthetic_incidents_100.csv" --source-col incident_text -c configs/my_config.json --mode release
```

## Output

- **Test mode (default):** prints source and masked text for each row to the terminal
- **Test mode (`--test-output`):** writes `test_output.csv` alongside the input CSV
- **Release mode:** writes a parquet file with all original columns preserved plus the new masked text column (default name: `masked_text`)

The parquet output is the expected input format for the downstream `data_extractor` component.

## Docker

Build from the Extracta project root:

```bash
docker build -f components/pii_cleanse/Dockerfile -t extracta-pii-cleanse components/pii_cleanse
```

The container mounts a `/data` volume for input and output. `OLLAMA_HOST` defaults to `http://host.docker.internal:11434` so the container can reach Ollama running on your Mac.

```bash
DATA="$(pwd)/applications/extracta/sample_data"

# Test mode — prints 5 rows to terminal
docker run --rm \
  -v "${DATA}:/data" \
  extracta-pii-cleanse \
  mistral-small:24b /data/synthetic_incidents_100.csv \
  --source-col incident_text

# Release mode — full dataset
docker run --rm \
  -v "${DATA}:/data" \
  extracta-pii-cleanse \
  mistral-small:24b /data/synthetic_incidents_100.csv \
  --source-col incident_text \
  --mode release \
  -o /data/synthetic_incidents_100_cleansed.parquet
```

Override the Ollama host if needed:

```bash
docker run --rm -e OLLAMA_HOST=http://host.docker.internal:11434 ...
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
