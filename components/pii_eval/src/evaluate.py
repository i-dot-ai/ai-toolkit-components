#!/usr/bin/env python3
"""
PII Redaction Evaluation CLI
Evaluates an Ollama model's PII masking against a ground truth dataset.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import date
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Set, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv
from openai import OpenAI
from seqeval.metrics import f1_score, precision_score, recall_score
from tqdm import tqdm

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_DATASET = "ai4privacy/open-pii-masking-500k-ai4privacy"
DEFAULT_SOURCE_COL = "source_text"
DEFAULT_GROUND_TRUTH_COL = "masked_text"


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a PII detection assistant. "
    "Replace every piece of personally identifiable information in the text "
    "with a bracketed label such as [EMAIL], [GIVENNAME], [SURNAME], [TEL], "
    "[DATE], [ADDRESS], [USERNAME], [IDCARDNUM], [POSTCODE], [IP], [URL], etc. "
    "Use the most specific label that applies. "
    "Return ONLY the masked text in JSON format with no explanation or commentary."
)


def call_model(source_text: str, model: str, provider: str) -> str:
    if provider == "openai":
        client = OpenAI()  # reads OPENAI_API_KEY from environment
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
                    {"role": "system", "content": SYSTEM_PROMPT},
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
# Tokenisation helpers
# ---------------------------------------------------------------------------

BRACKET_RE = re.compile(r"\[\[?[^\[\]]+\]\]?")


def _tokenise(text: str) -> List[str]:
    tokens: List[str] = []
    for chunk in re.split(r"\s+", text):
        if not chunk:
            continue
        idx = 0
        for m in BRACKET_RE.finditer(chunk):
            pre = chunk[idx : m.start()]
            if pre:
                tokens.append(pre.strip('"\':,'))
            tokens.append(m.group())
            idx = m.end()
        tail = chunk[idx:]
        if tail:
            tokens.append(tail.strip('"\':,'))
    return [t for t in tokens if t]


def collect_pii_labels(responses: List[str]) -> Set[str]:
    pattern = re.compile(r"\[([A-Za-z0-9_]+)\]")
    labels: Set[str] = set()
    for r in responses:
        if isinstance(r, str):
            labels.update(m.upper() for m in pattern.findall(r))
    return labels


def _make_predicates(special_labels: Iterable[str]):
    LABELS: Set[str] = {lbl.upper() for lbl in special_labels}

    def is_bracket(tok: str) -> bool:
        return bool(BRACKET_RE.fullmatch(tok))

    def extract_label(tok: str) -> str:
        return tok.strip("[]").upper()

    def is_special(tok: str) -> bool:
        return is_bracket(tok) and extract_label(tok) in LABELS

    return is_special, extract_label


# ---------------------------------------------------------------------------
# BIO sequence builder for seqeval
# ---------------------------------------------------------------------------

def to_bio_sequence(tokens: List[str], is_special, extract_label) -> List[str]:
    tags = []
    for tok in tokens:
        if is_special(tok):
            tags.append(f"B-{extract_label(tok)}")
        else:
            tags.append("O")
    return tags


def build_bio_pairs(
    outputs: List[str],
    grounds: List[str],
    special_labels: Iterable[str],
) -> Tuple[List[List[str]], List[List[str]]]:
    is_special, extract_label = _make_predicates(special_labels)
    pred_tags_all: List[List[str]] = []
    gold_tags_all: List[List[str]] = []

    for out, gold in zip(outputs, grounds):
        if not isinstance(out, str):
            continue
        pred_tokens = _tokenise(out)
        gold_tokens = _tokenise(gold)

        pred_bio = to_bio_sequence(pred_tokens, is_special, extract_label)
        gold_bio = to_bio_sequence(gold_tokens, is_special, extract_label)

        length = max(len(pred_bio), len(gold_bio))
        pred_bio += ["O"] * (length - len(pred_bio))
        gold_bio += ["O"] * (length - len(gold_bio))

        pred_tags_all.append(pred_bio)
        gold_tags_all.append(gold_bio)

    return pred_tags_all, gold_tags_all


# ---------------------------------------------------------------------------
# Token-level PII metrics
# ---------------------------------------------------------------------------

def _score_one_sample(
    out: str,
    gold: str,
    is_special,
) -> Tuple[int, int, int]:
    """
    Return (tp, fp, fn) for a single output/ground-truth pair.
    Shared by both the aggregate and per-sample metrics.
    """
    pred_tokens = _tokenise(out)
    gold_tokens = _tokenise(gold)
    sm = SequenceMatcher(a=pred_tokens, b=gold_tokens, autojunk=False)
    tp = fp = fn = 0

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for tok in pred_tokens[i1:i2]:
                if is_special(tok):
                    tp += 1
            continue
        if tag == "delete":
            fp += sum(is_special(t) for t in pred_tokens[i1:i2])
            continue
        if tag == "insert":
            fn += sum(is_special(t) for t in gold_tokens[j1:j2])
            continue
        width = max(i2 - i1, j2 - j1)
        for k in range(width):
            tok_pred = pred_tokens[i1 + k] if k < i2 - i1 else None
            tok_gold = gold_tokens[j1 + k] if k < j2 - j1 else None
            if tok_pred and tok_gold:
                g_sp = is_special(tok_gold)
                p_sp = is_special(tok_pred)
                if g_sp and p_sp:
                    tp += 1
                elif g_sp:
                    fn += 1
                elif p_sp:
                    fp += 1
            elif tok_pred and is_special(tok_pred):
                fp += 1
            elif tok_gold and is_special(tok_gold):
                fn += 1

    return tp, fp, fn


def token_pii_metrics(
    outputs: List[str],
    grounds: List[str],
    special_labels: Iterable[str],
) -> Dict:
    assert len(outputs) == len(grounds)
    is_special, _ = _make_predicates(special_labels)

    total = Counter(tp=0, fp=0, fn=0)
    exact_match = 0
    partial_match = 0
    n_valid = 0

    for out, gold in zip(outputs, grounds):
        if not isinstance(out, str):
            continue
        n_valid += 1

        if out.strip() == gold.strip():
            exact_match += 1

        tp, fp, fn = _score_one_sample(out, gold, is_special)
        total["tp"] += tp
        total["fp"] += fp
        total["fn"] += fn

        if tp > 0:
            partial_match += 1

    tp, fp, fn = total["tp"], total["fp"], total["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall    = tp / (tp + fn) if (tp + fn) else 0.0
    f1        = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0
    fnr       = fn / (tp + fn) if (tp + fn) else 0.0

    return {
        "precision":            precision,
        "recall":               recall,
        "f1":                   f1,
        "tp":                   tp,
        "fp":                   fp,
        "fn":                   fn,
        "false_negatives":      fn,
        "false_negative_rate":  fnr,
        "exact_match_count":    exact_match,
        "partial_match_count":  partial_match,
        "exact_match_rate":     exact_match / n_valid if n_valid else 0.0,
        "partial_match_rate":   partial_match / n_valid if n_valid else 0.0,
        "n_valid":              n_valid,
    }


def build_sample_log(
    source_texts: List[str],
    grounds: List[str],
    outputs: List[str],
    special_labels: Iterable[str],
    model: str,
    dataset_name: str,
    source_col: str,
    gt_col: str,
) -> pd.DataFrame:
    """
    Build a per-sample DataFrame with result label (match/miss) and fn count.
    A sample is a 'miss' if it has any false negatives (PII present in ground
    truth that the model did not redact).
    """
    is_special, _ = _make_predicates(special_labels)
    eval_date = date.today().isoformat()
    rows = []

    for src, gold, out in zip(source_texts, grounds, outputs):
        if not isinstance(out, str):
            rows.append({
                "model":          model,
                "evaluation_date": eval_date,
                "dataset":        dataset_name,
                "source_col":     source_col,
                "gt_col":         gt_col,
                "source_text":    src,
                "ground_truth":   gold,
                "model_output":   None,
                "result":         "error",
                "fn_count":       None,
            })
            continue

        _, _, fn = _score_one_sample(out, gold, is_special)
        rows.append({
            "model":          model,
            "evaluation_date": eval_date,
            "dataset":        dataset_name,
            "source_col":     source_col,
            "gt_col":         gt_col,
            "source_text":    src,
            "ground_truth":   gold,
            "model_output":   out,
            "result":         "miss" if fn > 0 else "match",
            "fn_count":       fn,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def load_ground_truth(
    config: dict,
    source_col: str,
    ground_truth_col: str,
    sample_size: int,
) -> Tuple[pd.DataFrame, str, str, Set[str]]:
    """
    Load dataset from config or default HuggingFace dataset.
    Returns (sample_df, source_col, ground_truth_col, special_tokens).
    """
    dataset_name = DEFAULT_DATASET
    special_tokens: Set[str] = set()

    if config:
        dataset_path = config.get("dataset_path")
        source_col = config.get("source_text_column", source_col)
        ground_truth_col = config.get("ground_truth_column", ground_truth_col)

        if dataset_path:
            print(f"Loading dataset from: {dataset_path}")
            if dataset_path.endswith(".csv"):
                df = pd.read_csv(dataset_path)
            elif dataset_path.endswith(".parquet"):
                df = pd.read_parquet(dataset_path)
            else:
                print(f"Error: unsupported file type for dataset_path: {dataset_path}", file=sys.stderr)
                sys.exit(1)

            dataset_name = dataset_path
            sample_df = df.head(sample_size).copy()

            # Strip numeric suffixes from ground truth column
            sample_df["_gt_stripped"] = sample_df[ground_truth_col].str.replace(
                r"\[([A-Z]+)_\d+\]", r"[\1]", regex=True
            )
            return sample_df, source_col, "_gt_stripped", special_tokens, dataset_name

    # Default: ai4privacy HuggingFace dataset
    load_dotenv()
    hf_token = os.getenv("HF_TOKEN")

    print(f"Loading dataset: {DEFAULT_DATASET}")
    from datasets import load_dataset
    ds = load_dataset(DEFAULT_DATASET, token=hf_token)
    train_data = ds["train"]

    df = train_data.to_pandas()
    df = df[df["language"] == "en"].reset_index(drop=True)

    # Strip numeric suffixes
    df["_gt_stripped"] = df[ground_truth_col].str.replace(
        r"\[([A-Z]+)_\d+\]", r"[\1]", regex=True
    )

    # Collect known PII label types from privacy_mask field
    for ls in train_data["privacy_mask"]:
        special_tokens.update({item["label"] for item in ls})

    sample_df = df.head(sample_size).copy()
    return sample_df, source_col, "_gt_stripped", special_tokens, dataset_name


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate an Ollama model's PII redaction against a ground truth dataset."
    )
    parser.add_argument("model", help='Ollama model name, e.g. "qwen2.5:32b"')
    parser.add_argument(
        "-o", "--output", default="pii_eval_results.csv",
        help="Path to results CSV (default: pii_eval_results.csv)"
    )
    parser.add_argument(
        "-n", "--sample-size", type=int, default=100,
        dest="sample_size",
        help="Number of samples to evaluate (default: 100)"
    )
    parser.add_argument(
        "-c", "--config",
        help="Path to JSON config file with dataset_path, source_text_column, ground_truth_column"
    )
    parser.add_argument(
        "--source-col", default=DEFAULT_SOURCE_COL,
        help=f"Source text column name (default: {DEFAULT_SOURCE_COL})"
    )
    parser.add_argument(
        "--gt-col", default=DEFAULT_GROUND_TRUTH_COL,
        help=f"Ground truth column name (default: {DEFAULT_GROUND_TRUTH_COL})"
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "-A", "--append", dest="mode", action="store_const", const="append",
        help="Append results to existing CSV (default if file exists)"
    )
    mode_group.add_argument(
        "-O", "--overwrite", dest="mode", action="store_const", const="overwrite",
        help="Overwrite existing CSV"
    )
    parser.set_defaults(mode=None)

    parser.add_argument(
        "-f", "--force", action="store_true",
        help="Force re-evaluation even if this model already has results in the output CSV"
    )
    parser.add_argument(
        "-p", "--provider", default="ollama", choices=["ollama", "openai"],
        help="Inference provider: ollama (default) or openai"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    MODEL = args.model
    SAMPLE_SIZE = args.sample_size
    output_path = args.output

    # Determine write mode
    file_exists = os.path.isfile(output_path)
    if args.mode == "overwrite":
        write_mode = "overwrite"
    elif args.mode == "append":
        write_mode = "append"
    else:
        # Default: append if file exists, create otherwise
        write_mode = "append" if file_exists else "overwrite"

    # Check for existing results for this model
    if file_exists and write_mode == "append" and not args.force:
        existing = pd.read_csv(output_path)
        if "model" in existing.columns and MODEL in existing["model"].values:
            prior = existing[existing["model"] == MODEL][["model", "evaluation_date", "sample_size"]].to_string(index=False)
            print(f"Model '{MODEL}' already has results in {output_path}:\n\n{prior}\n")
            print("Use -f to force re-evaluation, or -O to overwrite the file.")
            sys.exit(0)

    # Load config if provided
    config = {}
    if args.config:
        if not os.path.isfile(args.config):
            print(f"Error: config file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        with open(args.config) as f:
            config = json.load(f)

    # Load dataset
    sample_df, source_col, gt_col, special_tokens, dataset_name = load_ground_truth(
        config, args.source_col, args.gt_col, SAMPLE_SIZE
    )

    ground_truth = sample_df[gt_col].tolist()

    # Run inference
    if args.provider == "openai":
        load_dotenv()
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY not found in environment.", file=sys.stderr)
            sys.exit(1)

    model_outputs = []
    for text in tqdm(sample_df[source_col], desc=MODEL):
        try:
            model_outputs.append(call_model(text, MODEL, args.provider))
        except Exception as e:
            model_outputs.append(None)
            print(f"Error: {e}", file=sys.stderr)

    n_successful = sum(1 for o in model_outputs if o is not None)
    print(f"{MODEL} done — {n_successful}/{SAMPLE_SIZE} successful")

    # Compute metrics
    valid_pairs = [(o, g) for o, g in zip(model_outputs, ground_truth) if isinstance(o, str)]
    if not valid_pairs:
        print("Error: no valid responses to evaluate.", file=sys.stderr)
        sys.exit(1)

    outs, grnds = zip(*valid_pairs)
    outs, grnds = list(outs), list(grnds)

    all_labels = special_tokens | collect_pii_labels(model_outputs)

    tok = token_pii_metrics(outs, grnds, all_labels)

    pred_tags, gold_tags = build_bio_pairs(outs, grnds, all_labels)
    seq_precision = precision_score(gold_tags, pred_tags, zero_division=0)
    seq_recall    = recall_score(gold_tags, pred_tags, zero_division=0)
    seq_f1        = f1_score(gold_tags, pred_tags, zero_division=0)

    # Print summary
    print(f"\n{'='*60}")
    print(f"  {MODEL}  ({len(valid_pairs)}/{len(model_outputs)} valid responses)")
    print(f"{'='*60}")
    print(f"\n--- Token-level PII metrics (label-agnostic) ---")
    print(f"  Precision          : {tok['precision']:.3f}")
    print(f"  Recall             : {tok['recall']:.3f}")
    print(f"  F1                 : {tok['f1']:.3f}")
    print(f"  TP / FP / FN       : {tok['tp']} / {tok['fp']} / {tok['fn']}")
    print(f"  False Negatives    : {tok['false_negatives']}  (FN rate: {tok['false_negative_rate']:.3f})")
    print(f"\n--- Match quality against ground truth ---")
    print(f"  Exact Match        : {tok['exact_match_count']}/{tok['n_valid']} ({tok['exact_match_rate']:.1%})")
    print(f"  Partial Match      : {tok['partial_match_count']}/{tok['n_valid']} ({tok['partial_match_rate']:.1%})")
    print(f"\n--- seqeval entity-level metrics (micro-avg) ---")
    print(f"  Precision          : {seq_precision:.3f}")
    print(f"  Recall             : {seq_recall:.3f}")
    print(f"  F1                 : {seq_f1:.3f}")

    # Build results row
    results_row = {
        "model":                    MODEL,
        "evaluation_date":          date.today().isoformat(),
        "dataset":                  dataset_name,
        "sample_size":              SAMPLE_SIZE,
        "valid_responses":          len(valid_pairs),
        # Token-level
        "token_precision":          tok["precision"],
        "token_recall":             tok["recall"],
        "token_f1":                 tok["f1"],
        "tp":                       tok["tp"],
        "fp":                       tok["fp"],
        "fn":                       tok["fn"],
        "false_negatives":          tok["false_negatives"],
        "false_negative_rate":      tok["false_negative_rate"],
        # Match quality
        "exact_match_count":        tok["exact_match_count"],
        "exact_match_rate":         tok["exact_match_rate"],
        "partial_match_count":      tok["partial_match_count"],
        "partial_match_rate":       tok["partial_match_rate"],
        # seqeval entity-level
        "seqeval_precision":        seq_precision,
        "seqeval_recall":           seq_recall,
        "seqeval_f1":               seq_f1,
    }

    results_df = pd.DataFrame([results_row])

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Write summary output
    if write_mode == "append" and file_exists:
        existing = pd.read_csv(output_path)
        combined = pd.concat([existing, results_df], ignore_index=True)
        combined.to_csv(output_path, index=False)
        print(f"\nResults appended to: {output_path}")
    else:
        results_df.to_csv(output_path, index=False)
        print(f"\nResults saved to: {output_path}")

    # Write per-sample log
    base, ext = os.path.splitext(output_path)
    samples_path = f"{base}_samples{ext}"
    samples_df = build_sample_log(
        source_texts=sample_df[source_col].tolist(),
        grounds=sample_df[gt_col].tolist(),
        outputs=model_outputs,
        special_labels=all_labels,
        model=MODEL,
        dataset_name=dataset_name,
        source_col=source_col,
        gt_col=gt_col,
    )
    samples_file_exists = os.path.isfile(samples_path)
    if write_mode == "append" and samples_file_exists:
        existing_samples = pd.read_csv(samples_path)
        pd.concat([existing_samples, samples_df], ignore_index=True).to_csv(samples_path, index=False)
        print(f"Per-sample log appended to: {samples_path}")
    else:
        samples_df.to_csv(samples_path, index=False)
        print(f"Per-sample log saved to: {samples_path}")


if __name__ == "__main__":
    main()
