#!/usr/bin/env python3
"""
PII Cleanse CLI
Applies LLM-based PII masking to a CSV, producing a cleansed dataset
for downstream field extraction.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

DEFAULT_SENSITIVE_CONFIG = os.environ.get(
    "SENSITIVE_CONFIG",
    str(Path(__file__).resolve().parent.parent / "configs" / "sensitive_attr_config.json"),
)
DEFAULT_RUNTIME_CONFIG = os.environ.get(
    "RUNTIME_CONFIG",
    str(Path(__file__).resolve().parent.parent / "configs" / "runtime_config.json"),
)

_RUNTIME_DEFAULTS = {
    "ollama_timeout_seconds": 120,
    "output_format": "parquet",
    "source_col": "source_text",
    "output_col": "masked_text",
}


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
# System prompt
# ---------------------------------------------------------------------------

ENTITY_HINTS = {
    "POST CODE": "UK postcode, e.g. SW1A 2AA, M1 1AE, EH1 1YZ",
    "LOCATION": "place names such as cities, streets, stations — but NOT postcodes",
}


def build_system_prompt(config: dict) -> str:
    """
    Build a system prompt from sensitive_attr_config.
    action == "ignore"  → instruct LLM to leave unchanged
    anything else       → instruct LLM to replace with [LABEL]
    """
    lines = []
    for entity, action in config.items():
        hint = ENTITY_HINTS.get(entity, "")
        label = f"{entity} ({hint})" if hint else entity
        if action == "ignore":
            lines.append(f"- {label}: leave unchanged")
        else:
            lines.append(f"- {label}: replace with [{entity}]")
    rules = "\n".join(lines)
    return (
        "You are a PII detection assistant. "
        "Apply the following rules to the text:\n"
        f"{rules}\n"
        "Return ONLY the modified text with no explanation or commentary."
    )


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def call_model(
    source_text: str,
    model: str,
    provider: str,
    system_prompt: str,
    timeout: int,
) -> str:
    if provider == "openai":
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": source_text},
            ],
            temperature=0,
        )
        return response.choices[0].message.content
    else:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": source_text},
                ],
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Apply LLM-based PII masking to a CSV for downstream extraction."
    )
    parser.add_argument("model", help='Model name, e.g. "qwen2.5:32b" or "gpt-4o"')
    parser.add_argument("csv_path", help="Path to input CSV file")
    parser.add_argument(
        "-p", "--provider", default="ollama", choices=["ollama", "openai"],
        help="Inference provider: ollama (default) or openai",
    )
    parser.add_argument(
        "-c", "--sensitive-config", default=DEFAULT_SENSITIVE_CONFIG,
        dest="sensitive_config",
        help="Path to sensitive_attr_config.json (default: configs/sensitive_attr_config.json)",
    )
    parser.add_argument(
        "-r", "--runtime-config", default=DEFAULT_RUNTIME_CONFIG,
        dest="runtime_config",
        help="Path to runtime_config.json (default: configs/runtime_config.json)",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Output file path (overrides default derived from input filename)",
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

    # Validate credentials
    if args.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment.", file=sys.stderr)
        sys.exit(1)

    # Load configs
    runtime = load_runtime_config(args.runtime_config)

    config_path = args.sensitive_config
    if not os.path.isfile(config_path):
        print(f"Error: sensitive config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        sensitive_config = json.load(f)

    system_prompt = build_system_prompt(sensitive_config)

    source_col    = runtime["source_col"]
    output_col    = runtime["output_col"]
    output_format = runtime["output_format"]
    timeout       = int(runtime["ollama_timeout_seconds"])

    # Load CSV
    if not os.path.isfile(args.csv_path):
        print(f"Error: CSV not found: {args.csv_path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(args.csv_path)

    if source_col not in df.columns:
        print(
            f"Error: column '{source_col}' not found in CSV. "
            f"Available columns: {list(df.columns)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Preview mode — limit rows
    if args.preview is not None:
        df = df.head(args.preview).copy()

    # Inference
    model_outputs = []
    for text in tqdm(df[source_col], desc=args.model):
        try:
            model_outputs.append(
                call_model(text, args.model, args.provider, system_prompt, timeout)
            )
        except Exception as e:
            model_outputs.append(None)
            print(f"Error: {e}", file=sys.stderr)

    n_successful = sum(1 for o in model_outputs if o is not None)
    n_total = len(model_outputs)
    print(f"\n{args.model} done — {n_successful}/{n_total} successful")

    df[output_col] = model_outputs

    # Output
    stem = Path(args.csv_path).stem

    if output_format == "stdout":
        print()
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            print(f"Row {i}:")
            print(f"  SOURCE : {row[source_col]}")
            print(f"  MASKED : {row[output_col]}")
            print()

    elif output_format == "csv":
        out_path = args.output or os.path.join(
            os.path.dirname(args.csv_path), f"{stem}_cleansed.csv"
        )
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        df.to_csv(out_path, index=False)
        print(f"Cleansed dataset written to: {out_path}")

    else:  # parquet (default)
        out_path = args.output or os.path.join(
            os.path.dirname(args.csv_path), f"{stem}_cleansed.parquet"
        )
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        df.to_parquet(out_path, index=False)
        print(f"Cleansed dataset written to: {out_path}")


if __name__ == "__main__":
    main()
