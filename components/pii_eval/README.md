# PII Redaction Evaluation Tool

Evaluates an Ollama model's PII masking output against a labelled ground truth dataset. Produces token-level and entity-level (seqeval) metrics and appends results to a CSV for cross-model comparison.

## Prerequisites

- [Ollama](https://ollama.com/) installed and running locally with a model pulled, e.g. `ollama pull mistral-small:24b`
- [Docker](https://www.docker.com/)

> **Platform note:** The default `OLLAMA_HOST` (`host.docker.internal:11434`) works on Mac and Windows Docker Desktop. On Linux, `host.docker.internal` is not available by default — override it with the host's Docker bridge IP: `-e OLLAMA_HOST=http://172.17.0.1:11434`. On Windows, the recommended setup is to run both Ollama and Docker inside WSL2.

---

## What it measures

| Metric | Description |
|---|---|
| `token_precision` | Of all PII tags the model produced, what fraction were correct |
| `token_recall` | Of all PII tags in ground truth, what fraction did the model find |
| `token_f1` | Harmonic mean of token precision and recall |
| `tp / fp / fn` | Raw token-level true positives, false positives, false negatives |
| `false_negative_rate` | `fn / (tp + fn)` — missed-redaction risk signal |
| `exact_match_rate` | Fraction of samples where model output == ground truth exactly |
| `partial_match_rate` | Fraction of samples with at least one correct PII token |
| `seqeval_precision/recall/f1` | Entity-level NER metrics (micro-averaged) via seqeval |

## Dependencies

Requires Ollama running locally at `http://localhost:11434`.

For the default dataset (`ai4privacy/open-pii-masking-500k-ai4privacy`), a HuggingFace token is required. Add it to a `.env` file in this directory:

```
HF_TOKEN=hf_yourtoken
OPENAI_API_KEY=sk_yourkey
```

**Important:** values must be unquoted. Docker's `--env-file` treats quotes as literal characters and will fail to resolve the token if they are present. `python-dotenv` handles both formats, but unquoted values work correctly in both contexts.

The `.env` file is excluded from git and Docker build context via `.gitignore` and `.dockerignore`.

Python dependencies: `pandas`, `requests`, `python-dotenv`, `seqeval`, `tqdm`, `datasets`, `pyarrow`, `openai`.

## Config file (optional)

To use a local dataset instead of the default HuggingFace one, provide a JSON config file:

```json
{
    "dataset_path": "path/to/data.csv",
    "source_text_column": "source_text",
    "ground_truth_column": "masked_text"
}
```

Supported file types: `.csv`, `.parquet`. All fields are optional — omitted fields fall back to their defaults. If `dataset_path` is omitted the HuggingFace dataset is used regardless.

---

## CLI Usage

```
python evaluate.py <model> [options]
```

### Arguments

| Argument | Description |
|---|---|
| `model` | **Required.** Ollama model name, e.g. `qwen2.5:32b`, `llama3:8b` |
| `-n`, `--sample-size` | Number of samples to evaluate. Default: `100` |
| `-o`, `--output` | Path to results CSV. Default: `pii_eval_results.csv` |
| `-c`, `--config` | Path to JSON config file for custom dataset |
| `--source-col` | Source text column name. Default: `source_text` |
| `--gt-col` | Ground truth column name. Default: `masked_text` |
| `-A`, `--append` | Append results to existing CSV |
| `-O`, `--overwrite` | Overwrite existing CSV |
| `-f`, `--force` | Force re-evaluation even if results for this model already exist |
| `-p`, `--provider` | Inference provider: `ollama` (default) or `openai` |

### Output file behaviour

- If the output file **does not exist**, a new file is created regardless of `-A`/`-O`.
- If the output file **already exists** and neither flag is given, **`-A` (append) is the default**.
- `-A` and `-O` are mutually exclusive.
- If the chosen model **already appears** in the output CSV, the script will print the existing result rows and exit without running inference. Use `-f` to override this and re-evaluate anyway.

Each run appends (or writes) one row containing: `model`, `evaluation_date`, `dataset`, `sample_size`, and all evaluation metrics.

### Example Models Evaluated by MMLU Aggregate:
![phi4 MMLU score](phi4_mmlu.png)

### Examples

```bash
# Minimal — uses default dataset, 100 samples, appends to pii_eval_results.csv
python evaluate.py qwen2.5:32b

# Custom sample size and output path
python evaluate.py llama3:8b -n 500 -o results/llama3_eval.csv

# Use a local dataset via config file
python evaluate.py mistral-small:24b -c config.json -o results/mistral_eval.csv

# Explicitly overwrite the output file instead of appending
python evaluate.py qwen2.5:32b -O -o results/eval.csv

# Override column names directly without a config file
python evaluate.py qwen2.5:32b --source-col text --gt-col masked -o results/eval.csv
```

---

## Docker

### Build

Run from the Extracta project root:

```bash
docker build -t extracta-pii-eval components/pii_eval
```

### Running the container

The container mounts a `/data` volume for input datasets, config files, and output CSVs. Ollama must be running on the host machine — the container reaches it via `host.docker.internal:11434`.

**`HF_TOKEN` must never be set in the Dockerfile.** Pass it at runtime only, using `--env-file`. The `.env` file must use unquoted values:

```
HF_TOKEN=hf_yourtoken
```

**Default HuggingFace dataset, append to results CSV:**
```bash
docker run --rm --env-file pii_eval/.env -v "$(pwd)/pii_eval/results:/data" extracta-pii-eval mistral-small:24b -o /data/eval.csv
```

**Custom sample size:**
```bash
docker run --rm --env-file pii_eval/.env -v "$(pwd)/pii_eval/results:/data" extracta-pii-eval mistral-small:24b -n 50 -o /data/eval.csv
```

**Local dataset via config file** (mount your data directory to `/data`, config paths must reference `/data/...`):
```bash
docker run --rm -v "$(pwd)/dummy data:/data" extracta-pii-eval mistral-small:24b -c /data/eval_config.json -o /data/eval.csv
```

Where `eval_config.json` on your host references container-internal paths:
```json
{
    "dataset_path": "/data/synthetic_uk_rail_incident_logs_varied_100.csv",
    "source_text_column": "incident_text",
    "ground_truth_column": "masked_text"
}
```

**Force re-evaluation of a model already in results:**
```bash
docker run --rm --env-file pii_eval/.env -v "$(pwd)/pii_eval/results:/data" extracta-pii-eval mistral-small:24b -f -o /data/eval.csv
```

**Overwrite results entirely:**
```bash
docker run --rm --env-file pii_eval/.env -v "$(pwd)/pii_eval/results:/data" extracta-pii-eval mistral-small:24b -O -o /data/eval.csv
```

### Evaluating a new Ollama model

Pull the model on the host first, then pass it as the first argument to the container:

```bash
ollama pull llama3:8b

docker run --rm --env-file pii_eval/.env -v "$(pwd)/pii_eval/results:/data" extracta-pii-eval llama3:8b -o /data/eval.csv
```

The container reaches Ollama on the host via `host.docker.internal:11434`. All results are written to the mounted `/data` volume and persist after the container exits.
