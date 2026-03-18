#!/usr/bin/env python3
"""
Data Extraction CLI
Reads a PII-cleansed parquet (upstream output of pii_cleanse/cleanse.py),
extracts structured fields from the masked text column via Ollama, and
writes results to JSON. Field definitions are driven by a JSON config.
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
    str(Path(__file__).resolve().parent.parent / "configs" / "extracta_config.json"),
)
DEFAULT_TEXT_COL = "masked_text"

SYSTEM_PROMPT = (
    "You are a data extraction assistant. "
    "Extract structured information from text and return it as valid JSON. "
    "Be precise and follow the field descriptions exactly."
)


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

def call_ollama(model: str, user_prompt: str) -> dict:
    response = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",       # Ollama native JSON mode
            "options": {"temperature": 0},
        },
        timeout=120,
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
        help="Path to input parquet file (output of pii_cleanse/cleanse.py)"
    )
    parser.add_argument(
        "-m", "--model", default=DEFAULT_MODEL, dest="model",
        help=f"Ollama model name (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "-c", "--config", default=DEFAULT_CONFIG,
        help="Path to extraction config JSON (default: configs/extracta_config.json)"
    )
    parser.add_argument(
        "--text-col", default=None, dest="text_col",
        help="Override the text column from config (default: config text_column)"
    )
    parser.add_argument(
        "--mode", default="test", choices=["test", "release"],
        help="test: process a small sample; release: process full dataset (default: test)"
    )
    parser.add_argument(
        "-n", "--test-rows", type=int, default=5, dest="test_rows",
        help="Number of rows to process in test mode (default: 5)"
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output JSON path (default: <parquet_stem>_extracted.json alongside input)"
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    load_dotenv()

    # Load extraction config
    config_path = args.config
    if not os.path.isfile(config_path):
        print(f"Error: config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        config = json.load(f)

    fields_to_extract = config["fields_to_extract"]
    null_result = {f["name"]: None for f in fields_to_extract}
    drop_columns = config.get("drop_columns", [])

    # Resolve text column: CLI flag > config > fallback default
    text_col = args.text_col or config.get("text_column", DEFAULT_TEXT_COL)

    # Load parquet
    if not os.path.isfile(args.parquet_path):
        print(f"Error: parquet not found: {args.parquet_path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_parquet(args.parquet_path)

    if text_col not in df.columns:
        print(
            f"Error: column '{text_col}' not found in parquet. "
            f"Available columns: {list(df.columns)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Slice for test mode
    if args.mode == "test":
        df = df.head(args.test_rows).copy()

    print(f"Model    : {args.model}")
    print(f"Text col : {text_col}")
    print(f"Rows     : {len(df)}")
    print(f"Fields   : {', '.join(f['name'] for f in fields_to_extract)}")
    print()

    # Inference loop
    results = []
    n_errors = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc=args.model):
        text = str(row[text_col])
        prompt = create_extraction_prompt(text, fields_to_extract)

        try:
            extracted = call_ollama(args.model, prompt)
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

    # Resolve output path
    if args.output:
        out_path = args.output
    else:
        stem = Path(args.parquet_path).stem
        out_path = os.path.join(os.path.dirname(args.parquet_path), f"{stem}_extracted.json")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Output   : {out_path}")


if __name__ == "__main__":
    main()
