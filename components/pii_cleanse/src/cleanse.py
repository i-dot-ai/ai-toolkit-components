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
DEFAULT_SOURCE_COL = "source_text"
DEFAULT_OUTPUT_COL = "masked_text"


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
    action == "ignore" → instruct LLM to leave unchanged
    anything else     → instruct LLM to replace with [LABEL]
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

def call_model(source_text: str, model: str, provider: str, system_prompt: str) -> str:
    if provider == "openai":
        client = OpenAI()  # reads OPENAI_API_KEY from environment
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
            timeout=120,
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
        help="Inference provider: ollama (default) or openai"
    )
    parser.add_argument(
        "-c", "--sensitive-config", default=DEFAULT_SENSITIVE_CONFIG,
        dest="sensitive_config",
        help=f"Path to sensitive_attr_config.json (default: configs/sensitive_attr_config.json)"
    )
    parser.add_argument(
        "--source-col", default=DEFAULT_SOURCE_COL,
        dest="source_col",
        help=f"Source text column name (default: {DEFAULT_SOURCE_COL})"
    )
    parser.add_argument(
        "--output-col", default=DEFAULT_OUTPUT_COL,
        dest="output_col",
        help=f"Output column name for masked text (default: {DEFAULT_OUTPUT_COL})"
    )
    parser.add_argument(
        "--mode", default="test", choices=["test", "release"],
        help="test: process a small sample for eyeballing; release: process full dataset (default: test)"
    )
    parser.add_argument(
        "-n", "--test-rows", type=int, default=5,
        dest="test_rows",
        help="Number of rows to process in test mode (default: 5)"
    )
    parser.add_argument(
        "--test-output", action="store_true",
        dest="test_output",
        help="In test mode, write results to test_output.csv instead of printing to terminal"
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Release output path (default: <csv_stem>_cleansed.parquet)"
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

    # Load sensitive config
    config_path = args.sensitive_config
    if not os.path.isfile(config_path):
        print(f"Error: sensitive config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        sensitive_config = json.load(f)

    system_prompt = build_system_prompt(sensitive_config)

    # Load CSV
    if not os.path.isfile(args.csv_path):
        print(f"Error: CSV not found: {args.csv_path}", file=sys.stderr)
        sys.exit(1)
    df = pd.read_csv(args.csv_path)

    if args.source_col not in df.columns:
        print(
            f"Error: column '{args.source_col}' not found in CSV. "
            f"Available columns: {list(df.columns)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Slice for test mode
    if args.mode == "test":
        df = df.head(args.test_rows).copy()

    # Inference
    model_outputs = []
    for text in tqdm(df[args.source_col], desc=args.model):
        try:
            model_outputs.append(call_model(text, args.model, args.provider, system_prompt))
        except Exception as e:
            model_outputs.append(None)
            print(f"Error: {e}", file=sys.stderr)

    n_successful = sum(1 for o in model_outputs if o is not None)
    n_total = len(model_outputs)
    print(f"\n{args.model} done — {n_successful}/{n_total} successful")

    df[args.output_col] = model_outputs

    # Output
    if args.mode == "test" and not args.test_output:
        # Print to terminal
        print()
        for i, (_, row) in enumerate(df.iterrows(), start=1):
            print(f"Row {i}:")
            print(f"  SOURCE : {row[args.source_col]}")
            print(f"  MASKED : {row[args.output_col]}")
            print()
    elif args.mode == "test" and args.test_output:
        out_path = os.path.join(os.path.dirname(args.csv_path), "test_output.csv")
        df[[args.source_col, args.output_col]].to_csv(out_path, index=False)
        print(f"Test output written to: {out_path}")
    else:
        # Release mode → parquet
        if args.output:
            out_path = args.output
        else:
            stem = Path(args.csv_path).stem
            out_path = os.path.join(os.path.dirname(args.csv_path), f"{stem}_cleansed.parquet")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        df.to_parquet(out_path, index=False)
        print(f"Cleansed dataset written to: {out_path}")


if __name__ == "__main__":
    main()
