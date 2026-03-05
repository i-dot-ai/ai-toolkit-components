import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.test_utils import verify_service_health, wait_for_service


@pytest.fixture(scope="module")
def component_endpoint(request):
    """Fixture to manage a component service for tests"""
    service_name, internal_port = request.param

    # Build and start specific component
    subprocess.run(["docker", "compose", "build", service_name], check=True)
    subprocess.run(["docker", "compose", "up", "-d", service_name], check=True)

    # Wait for component to be ready
    wait_for_service(service_name)

    # If the component has a health check, wait for it to pass before yielding
    try:
        verify_service_health(service_name)
    except ValueError:
        pass  # No health check configured; running state is sufficient

    yield f"http://localhost:{internal_port}"

    # Cleanup component
    subprocess.run(["docker", "compose", "stop", service_name])
    subprocess.run(["docker", "compose", "rm", "-f", service_name])


@pytest.fixture(scope="module")
def application_endpoint(request, tmp_path_factory):
    """Set up a clean application directory, start all services, and yield the app dir."""
    app_name = request.param
    app_dir = tmp_path_factory.mktemp("app")

    # Copy docker-compose.yaml to clean directory
    src_compose = Path(f"applications/{app_name}/docker-compose.yaml")
    shutil.copy(src_compose, app_dir / "docker-compose.yaml")
    compose_file = app_dir / "docker-compose.yaml"

    # Pre-create volume mount directories so they are owned by the current user
    # rather than root (which happens when Docker creates them automatically)
    with open(compose_file) as f:
        compose_config = yaml.safe_load(f)
    for service in compose_config.get("services", {}).values():
        for volume in service.get("volumes", []):
            host_path = volume.split(":")[0]
            if host_path.startswith("./") or host_path.startswith("../"):
                (app_dir / host_path).mkdir(parents=True, exist_ok=True)

    # Start all services
    result = subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        cwd=app_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start application: {result.stderr}")

    # Fix ownership of volume mount directories — container entrypoints may
    # create subdirectories as root, making them unwritable by the test runner
    for service in compose_config.get("services", {}).values():
        for volume in service.get("volumes", []):
            host_path = volume.split(":")[0]
            if host_path.startswith("./") or host_path.startswith("../"):
                subprocess.run(
                    ["docker", "run", "--rm", "-v", f"{app_dir / host_path}:/mount",
                     "alpine", "chmod", "-R", "a+rwX", "/mount"],
                    capture_output=True,
                )

    yield app_dir

    # Cleanup containers
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down", "-v"],
        cwd=app_dir,
        capture_output=True,
    )
