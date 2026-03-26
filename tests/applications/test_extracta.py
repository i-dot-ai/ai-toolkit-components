import subprocess
from pathlib import Path

import pytest
import yaml

from tests.test_utils import build_application_images

APP_NAME = "extracta"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_APP_DIR = _REPO_ROOT / "applications" / APP_NAME


class TestExtractaApplication:
    """Smoke tests for the Extracta batch pipeline application."""

    def test_docker_compose_is_valid(self):
        """Verify the application docker-compose.yaml parses and has all three services."""
        compose_file = _APP_DIR / "docker-compose.yaml"
        assert compose_file.exists(), "applications/extracta/docker-compose.yaml missing"
        with open(compose_file) as f:
            config = yaml.safe_load(f)
        services = config.get("services", {})
        assert "pii_cleanse" in services
        assert "data_extractor" in services
        assert "pii_eval" in services

    def test_sample_data_exists(self):
        """Verify sample data file is present and non-empty."""
        sample_data = _APP_DIR / "sample_data" / "synthetic_incidents_100.csv"
        assert sample_data.exists(), "sample_data/synthetic_incidents_100.csv missing"
        lines = sample_data.read_text().strip().split("\n")
        assert len(lines) > 1, "Sample data file has no rows"

    def test_component_images_build(self):
        """Verify all three component images build successfully from the compose file."""
        compose_file = _APP_DIR / "docker-compose.yaml"
        with open(compose_file) as f:
            config = yaml.safe_load(f)
        build_application_images(config)

    def test_pii_cleanse_container_starts(self):
        """Verify pii_cleanse image runs and responds to --help."""
        result = subprocess.run(
            ["docker", "run", "--rm", "extracta-pii-cleanse", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pii_cleanse --help failed:\n{result.stderr}"

    def test_data_extractor_container_starts(self):
        """Verify data_extractor image runs and responds to --help."""
        result = subprocess.run(
            ["docker", "run", "--rm", "extracta-data-extractor", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"data_extractor --help failed:\n{result.stderr}"

    def test_pii_eval_container_starts(self):
        """Verify pii_eval image runs and responds to --help."""
        result = subprocess.run(
            ["docker", "run", "--rm", "extracta-pii-eval", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"pii_eval --help failed:\n{result.stderr}"
