"""
Component tests for components/pii_eval.
Builds the Docker image and runs it against the Ollama stub using a local
dataset (no HuggingFace token required).
Requires Docker to be running.
"""
import csv
import shutil
from pathlib import Path

import pytest

from tests.components.conftest import run_component

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Minimal config pointing at the local fixture dataset
EVAL_CONFIG = """{
    "dataset_path": "/data/eval_dataset.csv",
    "source_text_column": "source_text",
    "ground_truth_column": "masked_text"
}
"""


class TestPiiEvalComponent:

    def test_help_exits_zero(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        result = run_component(
            pii_eval_image,
            ["--help"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_missing_config_file_exits_nonzero(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        result = run_component(
            pii_eval_image,
            ["stub-model", "-c", "/data/nonexistent_config.json"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_missing_dataset_exits_nonzero(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        config = '{"dataset_path": "/data/no_such_file.csv"}'
        (tmp_path / "eval_config.json").write_text(config)
        result = run_component(
            pii_eval_image,
            ["stub-model", "-c", "/data/eval_config.json", "-n", "1"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_local_dataset_exits_zero(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "eval_dataset.csv", tmp_path / "eval_dataset.csv")
        (tmp_path / "eval_config.json").write_text(EVAL_CONFIG)
        result = run_component(
            pii_eval_image,
            [
                "stub-model",
                "-c", "/data/eval_config.json",
                "-n", "2",
                "-o", "/data/results.csv",
            ],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0, result.stderr

    def test_produces_results_csv(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "eval_dataset.csv", tmp_path / "eval_dataset.csv")
        (tmp_path / "eval_config.json").write_text(EVAL_CONFIG)
        run_component(
            pii_eval_image,
            [
                "stub-model",
                "-c", "/data/eval_config.json",
                "-n", "2",
                "-o", "/data/results.csv",
            ],
            docker_network,
            tmp_path,
        )
        assert (tmp_path / "results.csv").exists()

    def test_results_csv_has_metrics_columns(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "eval_dataset.csv", tmp_path / "eval_dataset.csv")
        (tmp_path / "eval_config.json").write_text(EVAL_CONFIG)
        run_component(
            pii_eval_image,
            [
                "stub-model",
                "-c", "/data/eval_config.json",
                "-n", "2",
                "-o", "/data/results.csv",
            ],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "results.csv") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        for col in ["model", "token_precision", "token_recall", "token_f1", "false_negative_rate"]:
            assert col in headers, f"Expected column '{col}' in results CSV"

    def test_produces_per_sample_csv(self, pii_eval_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "eval_dataset.csv", tmp_path / "eval_dataset.csv")
        (tmp_path / "eval_config.json").write_text(EVAL_CONFIG)
        run_component(
            pii_eval_image,
            [
                "stub-model",
                "-c", "/data/eval_config.json",
                "-n", "2",
                "-o", "/data/results.csv",
            ],
            docker_network,
            tmp_path,
        )
        assert (tmp_path / "results_samples.csv").exists()
