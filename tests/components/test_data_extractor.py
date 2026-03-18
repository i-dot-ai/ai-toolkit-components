"""
Component tests for components/data_extractor.
Builds the Docker image and runs it against the Ollama stub.
Requires Docker to be running.
"""
import json
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

    def test_wrong_text_column_exits_nonzero(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        result = run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "--text-col", "no_such_column"],
            docker_network,
            tmp_path,
        )
        assert result.returncode != 0

    def test_test_mode_exits_zero(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        result = run_component(
            data_extractor_image,
            ["/data/cleansed.parquet", "--mode", "test", "-n", "1"],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0, result.stderr

    def test_release_mode_produces_json(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        result = run_component(
            data_extractor_image,
            [
                "/data/cleansed.parquet",
                "--mode", "release",
                "-o", "/data/extracted.json",
            ],
            docker_network,
            tmp_path,
        )
        assert result.returncode == 0, result.stderr
        assert (tmp_path / "extracted.json").exists()

    def test_output_json_is_valid_list(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        run_component(
            data_extractor_image,
            [
                "/data/cleansed.parquet",
                "--mode", "release",
                "-o", "/data/extracted.json",
            ],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "extracted.json") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_output_records_have_expected_fields(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        run_component(
            data_extractor_image,
            [
                "/data/cleansed.parquet",
                "--mode", "release",
                "-o", "/data/extracted.json",
            ],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "extracted.json") as f:
            data = json.load(f)
        for record in data:
            for field in ["issue", "impact", "resolution_action", "severity_indicator"]:
                assert field in record, f"Field '{field}' missing from record"

    def test_drop_columns_not_in_output(self, data_extractor_image, docker_network, ollama_stub, tmp_path):
        """Columns in drop_columns (incident_text, ner_labels) must not appear in output."""
        shutil.copy(FIXTURES / "cleansed.parquet", tmp_path / "cleansed.parquet")
        run_component(
            data_extractor_image,
            [
                "/data/cleansed.parquet",
                "--mode", "release",
                "-o", "/data/extracted.json",
            ],
            docker_network,
            tmp_path,
        )
        with open(tmp_path / "extracted.json") as f:
            data = json.load(f)
        for record in data:
            assert "incident_text" not in record
            assert "ner_labels" not in record
