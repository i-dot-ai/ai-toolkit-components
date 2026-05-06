# Running the Extracta tests

This directory contains unit and component tests for the three Extracta components:
`pii_cleanse`, `data_extractor`, and `pii_eval`.

## Prerequisites

Install test dependencies (from the repo root):

```bash
uv sync --extra test
```

Or with pip:

```bash
pip install -e ".[test]"
```

---

## Unit tests

No Docker, no Ollama, no network access required — all LLM calls are mocked.

```bash
pytest tests/unit/test_pii_cleanse.py tests/unit/test_data_extractor.py tests/unit/test_pii_eval.py -v
```

---

## Component tests

Require Docker to be running. A lightweight Ollama stub is used — no real model or
Ollama installation needed.

The stub mimics the Ollama `/api/chat` endpoint and returns canned responses,
so the components can be tested end-to-end without any LLM inference.

```bash
pytest tests/components/test_pii_cleanse.py tests/components/test_data_extractor.py tests/components/test_pii_eval.py -v
```

On first run, Docker will build the three component images and the stub image.
Subsequent runs reuse the cached images.

---

## Test structure

| Directory | What it tests | Requires |
|---|---|---|
| `tests/unit/` | Pure logic — prompt building, tokenisation, metrics | Nothing external |
| `tests/components/` | Each component's Docker image end-to-end | Docker |
| `tests/components/ollama_stub/` | Lightweight Flask stub mimicking Ollama `/api/chat` | — |
| `tests/components/fixtures/` | Small static input files (CSV, parquet) | — |
