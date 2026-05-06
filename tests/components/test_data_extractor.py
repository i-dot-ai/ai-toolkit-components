"""
Component tests for components/data_extractor.
Builds the Docker image and runs it against the Ollama stub.
Requires Docker to be running.
"""
import csv
import shutil
from pathlib import Path

import pytest

from tests.components.conftest import run_component

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestDataExtractorComponent:

    def test_help_exits_zero(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        result = run_component(
            data_extractor_image,
            ["--help"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

    def test_missing_input_file_exits_nonzero(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        result = run_component(
            data_extractor_image,
            ["/data/nonexistent.parquet"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_wrong_source_column_exits_nonzero(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        # incidents.csv converted to parquet — has incident_text not masked_text,
        # so it will fail the source_col check from runtime_config.json
        import pandas as pd
        df = pd.read_csv(FIXTURES / "incidents.csv")
        df.to_parquet(tmp_path / "wrong_col.parquet", index=False)
        result = run_component(
            data_extractor_image,
            ["/data/wrong_col.parquet"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_preview_exits_zero(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        result = run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "-n", "1"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0, result.stderr

    def test_full_run_produces_csv(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        result = run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "-o", "/data/extracted.csv"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "extracted.csv").exists()

    def test_output_csv_is_valid(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "-o", "/data/extracted.csv"],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "extracted.csv") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2

    def test_output_records_have_expected_fields(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "-o", "/data/extracted.csv"],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "extracted.csv") as f:
            rows = list(csv.DictReader(f))
        for record in rows:
            for field in ["issue", "impact", "resolution_action", "severity_indicator"]:
                assert field in record, f"Field '{field}' missing from record"

    def test_drop_columns_not_in_output(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        """Columns in drop_columns (incident_text, ner_labels) must not appear in output."""
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "-o", "/data/extracted.csv"],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "extracted.csv") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        assert "incident_text" not in headers
        assert "ner_labels" not in headers
