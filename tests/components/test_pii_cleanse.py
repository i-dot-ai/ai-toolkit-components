"""
Component tests for components/pii_cleanse.
Builds the Docker image and runs it against the Ollama stub.
Requires Docker to be running.
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from tests.components.conftest import run_component

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestPiiCleanseComponent:

    def test_help_exits_zero(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        result = run_component(
            pii_cleanse_image,
            ["--help"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_missing_input_file_exits_nonzero(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        result = run_component(
            pii_cleanse_image,
            ["stub-model", "/data/nonexistent.csv"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_wrong_source_column_exits_nonzero(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        # eval_dataset.csv has source_text/masked_text columns, not incident_text
        # so it will fail the source_col check from runtime_config.json
        shutil.copy(FIXTURES / "eval_dataset.csv", tmp_path / "eval_dataset.csv")
        result = run_component(
            pii_cleanse_image,
            ["stub-model", "/data/eval_dataset.csv"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_preview_exits_zero(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "incidents.csv", tmp_path / "incidents.csv")
        result = run_component(
            pii_cleanse_image,
            ["stub-model", "/data/incidents.csv", "-n", "1"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0

    def test_full_run_produces_parquet(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "incidents.csv", tmp_path / "incidents.csv")
        result = run_component(
            pii_cleanse_image,
            ["stub-model", "/data/incidents.csv", "-o", "/data/output.parquet"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "output.parquet").exists()

    def test_output_parquet_has_masked_text_column(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        import pandas as pd
        shutil.copy(FIXTURES / "incidents.csv", tmp_path / "incidents.csv")
        run_component(
            pii_cleanse_image,
            ["stub-model", "/data/incidents.csv", "-o", "/data/output.parquet"],
            docker_network,
            tmp_path,
        )
        df = pd.read_parquet(tmp_path / "output.parquet")
        assert "masked_text" in df.columns

    def test_output_parquet_has_correct_row_count(self, pii_cleanse_image, docker_network, ollama_stub, tmp_path):
        import pandas as pd
        shutil.copy(FIXTURES / "incidents.csv", tmp_path / "incidents.csv")
        run_component(
            pii_cleanse_image,
            ["stub-model", "/data/incidents.csv", "-o", "/data/output.parquet"],
            docker_network,
            tmp_path,
        )
        df = pd.read_parquet(tmp_path / "output.parquet")
        assert len(df) == 2
