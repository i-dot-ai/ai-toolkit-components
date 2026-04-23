#!/usr/bin/env python3
"""
Data Extraction CLI
Reads a PII-cleansed parquet (upstream output of pii_cleanse/cleanse.py),
extracts structured fields from the masked text column via Ollama, and
writes results to the format specified in runtime_config.json.
Field definitions are driven by a JSON config.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

DEFAULT_MODEL = "mistral-small:24b"
DEFAULT_CONFIG = os.environ.get(
    "EXTRACT_CONFIG",
    str(Path(__file__).resolve().parent.parent / "configs" / "fields_config.json"),
)
DEFAULT_RUNTIME_CONFIG = os.environ.get(
    "RUNTIME_CONFIG",
    str(Path(__file__).resolve().parent.parent / "configs" / "runtime_config.json"),
)

_RUNTIME_DEFAULTS = {
    "ollama_timeout_seconds": 120,
    "output_format": "csv",
    "source_col": "masked_text",
}

SYSTEM_PROMPT = (
    "You are a data extraction assistant. "
    "Extract structured information from text and return it as valid JSON. "
    "Be precise and follow the field descriptions exactly."
)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_runtime_config(path: str) -> dict:
    """Load runtime_config.json, merging over built-in defaults."""
    if os.path.isfile(path):
        with open(path) as f:
            return {**_RUNTIME_DEFAULTS, **json.load(f)}
    print(
        f"Warning: runtime config not found at {path}, using defaults.",
        file=sys.stderr,
    )
    return dict(_RUNTIME_DEFAULTS)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def create_extraction_prompt(text: str, fields_config: list) -> str:
    field_descriptions = "\n".join(
        f"- {f['name']}: {f['description']}" for f in fields_config
    )
    return (
        f"Extract the following information from the text below and return "
        f"ONLY a valid JSON object with these fields:\n\n"
        f"{field_descriptions}\n\n"
        f"Text to analyze:\n{text}\n\n"
        f"Return your response as a JSON object with the exact field names "
        f"specified above. For lists, use JSON arrays. "
        f"If information is not found, use null."
    )


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def call_ollama(model: str, user_prompt: str, timeout: int) -> dict:
    response = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    return json.loads(content)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Extract structured fields from a PII-cleansed parquet via Ollama."
    )
    parser.add_argument(
        "parquet_path",
        help="Path to input parquet file (output of pii_cleanse/cleanse.py)",
    )
    parser.add_argument(
        "-m", "--model", default=DEFAULT_MODEL, dest="model",
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-c", "--config", default=DEFAULT_CONFIG,
        help="Path to extraction config JSON (default: configs/fields_config.json)",
    )
    parser.add_argument(
        "-r", "--runtime-config", default=DEFAULT_RUNTIME_CONFIG,
        dest="runtime_config",
        help="Path to runtime_config.json (default: configs/runtime_config.json)",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Override output file path (default: derived from input filename)",
    )
    parser.add_argument(
        "-n", "--preview", type=int, default=None, dest="preview",
        metavar="N",
        help="Process only the first N rows — useful for quickly eyeballing model output",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    load_dotenv()

    # Load configs
    runtime = load_runtime_config(args.runtime_config)

    config_path = args.config
    if not os.path.isfile(config_path):
        print(f"Error: config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        config = json.load(f)

    fields_to_extract = config["fields_to_extract"]
    null_result = {f["name"]: None for f in fields_to_extract}
    drop_columns = config.get("drop_columns", [])

    source_col    = runtime["source_col"]
    output_format = runtime["output_format"]
    timeout       = int(runtime["ollama_timeout_seconds"])

    # Load parquet
    if not os.path.isfile(args.parquet_path):
        print(f"Error: parquet not found: {args.parquet_path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_parquet(args.parquet_path)

    if source_col not in df.columns:
        print(
            f"Error: column '{source_col}' not found in parquet. "
            f"Available columns: {list(df.columns)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Preview mode — limit rows
    if args.preview is not None:
        df = df.head(args.preview).copy()

    print(f"Model    : {args.model}")
    print(f"Text col : {source_col}")
    print(f"Rows     : {len(df)}")
    print(f"Fields   : {', '.join(f['name'] for f in fields_to_extract)}")
    print()

    # Inference loop
    results = []
    n_errors = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc=args.model):
        text = str(row[source_col])
        prompt = create_extraction_prompt(text, fields_to_extract)

        try:
            extracted = call_ollama(args.model, prompt, timeout)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            extracted = null_result.copy()
            n_errors += 1

        result = row.to_dict()
        for col in drop_columns:
            result.pop(col, None)
        result.update(extracted)
        results.append(result)

    print(f"\nDone — {len(results) - n_errors}/{len(results)} successful")

    stem = Path(args.parquet_path).stem

    # Output
    if output_format == "stdout":
        print()
        for i, r in enumerate(results, start=1):
            print(f"--- Row {i} ---")
            print(json.dumps(r, indent=2, default=str))
            print()

    elif output_format == "json":
        out_path = args.output or os.path.join(
            os.path.dirname(args.parquet_path), f"{stem}_extracted.json"
        )
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Output   : {out_path}")

    else:  # csv (default)
        out_path = args.output or os.path.join(
            os.path.dirname(args.parquet_path), f"{stem}_extracted.csv"
        )
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        pd.DataFrame(results).to_csv(out_path, index=False)
        print(f"Output   : {out_path}")


if __name__ == "__main__":
    main()
