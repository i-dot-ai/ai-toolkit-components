"""
Session-scoped fixtures for component tests.

Sets up:
  - A Docker network shared by the stub and component containers
  - The Ollama stub container (mimics /api/chat without a real LLM)
  - Pre-built Docker images for each component

Each test module receives the network name and stub container name so it
can pass OLLAMA_HOST=http://ollama-stub:11434 to the component under test.
"""
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
NETWORK = "extracta-test-net"
STUB_NAME = "ollama-stub"
STUB_IMAGE = "extracta-ollama-stub"


def _docker(*args, check=True, capture=False):
    kwargs = {"check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(["docker", *args], **kwargs)


# ---------------------------------------------------------------------------
# Docker network
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def docker_network():
    _docker("network", "create", NETWORK, check=False)
    yield NETWORK
    _docker("network", "rm", NETWORK, check=False)


# ---------------------------------------------------------------------------
# Ollama stub
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def ollama_stub(docker_network):
    stub_dir = Path(__file__).resolve().parent / "ollama_stub"
    _docker("build", "-t", STUB_IMAGE, str(stub_dir))
    _docker(
        "run", "-d", "--rm",
        "--name", STUB_NAME,
        "--network", docker_network,
        STUB_IMAGE,
    )
    # Wait for Flask to be ready
    time.sleep(3)
    yield STUB_NAME
    _docker("stop", STUB_NAME, check=False)


# ---------------------------------------------------------------------------
# Component images (built once per session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def pii_cleanse_image():
    _docker("build", "-t", "test-pii-cleanse", str(ROOT / "components" / "pii_cleanse"))
    return "test-pii-cleanse"


@pytest.fixture(scope="session")
def data_extractor_image():
    _docker("build", "-t", "test-data-extractor", str(ROOT / "components" / "data_extractor"))
    return "test-data-extractor"


@pytest.fixture(scope="session")
def pii_eval_image():
    _docker("build", "-t", "test-pii-eval", str(ROOT / "components" / "pii_eval"))
    return "test-pii-eval"


# ---------------------------------------------------------------------------
# Helpers available to all component tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fixtures_dir():
    return FIXTURES


def run_component(image, args, network, data_dir, env=None):
    """
    Run a component container with --rm, mounted data volume, and stub Ollama.
    Returns CompletedProcess (exit code + captured stdout/stderr).
    """
    cmd = [
        "docker", "run", "--rm",
        "--network", network,
        "-v", f"{data_dir}:/data",
        "-e", f"OLLAMA_HOST=http://{STUB_NAME}:11434",
    ]
    for k, v in (env or {}).items():
        cmd += ["-e", f"{k}={v}"]
    cmd.append(image)
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True)
