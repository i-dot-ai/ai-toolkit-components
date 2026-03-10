import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml

# Make shared modules (e.g. registry) importable in unit tests,
# mirroring the PYTHONPATH set in each component's Dockerfile.
_common = str(Path(__file__).resolve().parents[1] / "common")
if _common not in sys.path:
    sys.path.insert(0, _common)

from tests.test_utils import ComposeProject, _find_free_port

# Unique suffix appended to every project name so concurrent test runs never
# collide, while fixtures that share a base project name still share a network.
_SESSION_SUFFIX = uuid.uuid4().hex[:6]

# Port env vars to override per service so tests never conflict with a running
# dev stack.  All listed vars use a free host port; the first is the primary
# HTTP port used to build the URL.
_SERVICE_PORT_ENVS: dict[str, list[str]] = {
    "vector_db": ["VECTOR_DB_HTTP_PORT", "VECTOR_DB_GRPC_PORT"],
    "mcp_server": ["MCP_SERVER_PORT"],
}

# Shared compose_env per unique project name so component_endpoint and
# component_service fixtures that target the same project agree on ports.
_project_compose_envs: dict[str, dict] = {}


@pytest.fixture(scope="module")
def component_endpoint(request):
    """Fixture to manage a component service for tests.

    Param is a 3-tuple: (service_name, port, project).
    Use a shared project name when two fixtures must share a Docker network.
    """
    service_name, internal_port, project = request.param
    unique_project = f"{project}-{_SESSION_SUFFIX}"

    # Assign free ports to all port env vars for this service so the test
    # containers do not clash with a running dev stack.
    port_envs = _SERVICE_PORT_ENVS.get(service_name, [])
    compose_env = {env_var: str(_find_free_port()) for env_var in port_envs}
    _project_compose_envs[unique_project] = compose_env

    # The first free port (primary HTTP port) is used for the URL.
    url_port = compose_env[port_envs[0]] if port_envs else internal_port
    compose = ComposeProject(
        project=unique_project,
        url=f"http://localhost:{url_port}",
        compose_env=compose_env,
    )

    compose.build(service_name, check=True)
    result = compose.up(service_name, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose up {service_name} failed (rc={result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )
    compose.wait_for(service_name)

    try:
        compose.verify_health(service_name)
    except ValueError:
        pass  # No health check configured; running state is sufficient

    yield compose

    compose.stop(service_name)
    compose.rm(service_name)


@pytest.fixture(scope="module")
def component_service(request):
    """Start a long-running component that has no HTTP endpoint (e.g. a CLI service).

    Param is a 2-tuple: (service_name, project).
    Use a shared project name when two fixtures must share a Docker network.
    """
    service_name, project = request.param
    unique_project = f"{project}-{_SESSION_SUFFIX}"

    # Reuse any compose_env already established for this project (e.g. port
    # overrides set by a co-running component_endpoint fixture).
    compose_env = _project_compose_envs.get(unique_project, {})
    compose = ComposeProject(project=unique_project, compose_env=compose_env)

    compose.build(service_name, check=True)
    result = compose.up(service_name, "--no-deps", capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"docker compose up {service_name} failed (rc={result.returncode}):\n"
            f"{result.stderr or result.stdout}"
        )
    compose.wait_for(service_name)

    yield compose

    compose.stop(service_name)
    compose.rm(service_name)


@pytest.fixture(scope="module")
def application_endpoint(request, tmp_path_factory):
    """Set up a clean application directory, start all services, and yield a ComposeProject."""
    app_name = request.param
    app_dir = tmp_path_factory.mktemp("app")

    src_compose = Path(f"applications/{app_name}/docker-compose.yaml")
    shutil.copy(src_compose, app_dir / "docker-compose.yaml")
    compose_file = app_dir / "docker-compose.yaml"

    compose = ComposeProject(
        project=f"test-{app_name}-{_SESSION_SUFFIX}",
        compose_file=compose_file,
        app_dir=app_dir,
    )

    # Pre-create volume mount directories so they are owned by the current user
    # rather than root (which happens when Docker creates them automatically)
    with open(compose_file) as f:
        compose_config = yaml.safe_load(f)
    for service in compose_config.get("services", {}).values():
        for volume in service.get("volumes", []):
            host_path = volume.split(":")[0]
            if host_path.startswith("./") or host_path.startswith("../"):
                (app_dir / host_path).mkdir(parents=True, exist_ok=True)

    result = compose.up(capture_output=True, text=True)
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

    yield compose

    compose.down(capture_output=True)
