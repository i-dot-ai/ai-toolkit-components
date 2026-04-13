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


from tests.test_utils import ComposeProject, assign_ports, build_application_images

# Unique suffix appended to every project name so concurrent test runs never
# collide, while fixtures that share a base project name still share a network.
_SESSION_SUFFIX = uuid.uuid4().hex[:6]


@pytest.fixture(scope="module")
def port_env_map(request):
    """Assign a free port to each env var name supplied via indirect parametrize.

    The first entry is used as the primary HTTP port by ``component_endpoint``.
    Parametrize at the test-class level with the env vars needed for the service
    group under test.  When two classes in the same module pass identical lists,
    pytest shares the same fixture instance so they agree on ports::

        _PORT_VARS = ["MCP_SERVER_PORT", "VECTOR_DB_HTTP_PORT", "VECTOR_DB_GRPC_PORT"]

        @pytest.mark.parametrize("port_env_map", [_PORT_VARS], indirect=True)
        class TestMcpServer:
            ...
    """
    env_var_names = getattr(request, "param", [])
    return assign_ports(*env_var_names)


@pytest.fixture(scope="module")
def component_endpoint(request, port_env_map):
    """Fixture to manage a component service for tests.

    Param is a 2-tuple: (service_name, project).
    Use a shared project name when two fixtures must share a Docker network.

    Free ports are provided by the ``port_env_map`` fixture so that all
    port env vars for the whole service group are assigned once and shared
    consistently across fixtures that target the same project.
    """
    service_name, project = request.param
    unique_project = f"{project}-{_SESSION_SUFFIX}"

    url_port = next(iter(port_env_map.values()), None)
    if url_port is None:
        raise ValueError(
            f"port_env_map is empty for service '{service_name}'; "
            f"parametrize 'port_env_map' with the required env var names."
        )

    compose = ComposeProject(
        project=unique_project,
        url=f"http://localhost:{url_port}",
        compose_env=port_env_map,
    )

    compose.build(service_name, check=True)
    try:
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
    except Exception:
        compose.down(capture_output=True)
        raise

    yield compose

    compose.stop(service_name)
    compose.rm(service_name)


@pytest.fixture(scope="module")
def component_service(request, port_env_map):
    """Start a long-running component that has no HTTP endpoint (e.g. a CLI service).

    Param is a 2-tuple: (service_name, project).
    Use a shared project name when two fixtures must share a Docker network.

    Port env vars are inherited from ``port_env_map`` so the service connects
    to its dependencies on the same ports as the co-running component_endpoint.
    """
    service_name, project = request.param
    unique_project = f"{project}-{_SESSION_SUFFIX}"

    compose = ComposeProject(project=unique_project, compose_env=port_env_map)

    compose.build(service_name, check=True)
    try:
        result = compose.up(service_name, "--no-deps", capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"docker compose up {service_name} failed (rc={result.returncode}):\n"
                f"{result.stderr or result.stdout}"
            )
        compose.wait_for(service_name)
    except Exception:
        compose.down(capture_output=True)
        raise

    yield compose

    compose.stop(service_name)
    compose.rm(service_name)


@pytest.fixture(scope="module")
def application_endpoint(request, port_env_map, tmp_path_factory):
    """Set up a clean application directory, start all services, and yield a ComposeProject.

    Free ports are provided by the ``port_env_map`` fixture; parametrize it with
    all port env vars for the application, primary service port first.  The
    primary port becomes ``compose.url``.
    """
    app_name = request.param
    app_dir = tmp_path_factory.mktemp("app")

    src_compose = Path(f"applications/{app_name}/docker-compose.yaml")
    shutil.copy(src_compose, app_dir / "docker-compose.yaml")
    compose_file = app_dir / "docker-compose.yaml"

    url = f"http://localhost:{next(iter(port_env_map.values()))}" if port_env_map else None
    compose = ComposeProject(
        project=f"test-{app_name}-{_SESSION_SUFFIX}",
        compose_file=compose_file,
        app_dir=app_dir,
        url=url,
        compose_env=port_env_map,
    )

    # Pre-create volume mount directories so they are owned by the current user
    # rather than root (which happens when Docker creates them automatically)
    with open(compose_file) as f:
        compose_config = yaml.safe_load(f)
    for service in compose_config.get("services", {}).values():
        for volume in service.get("volumes", []):
            host_path = volume.split(":")[0]
            if host_path.startswith("./") or host_path.startswith("../"):
                d = app_dir / host_path
                d.mkdir(parents=True, exist_ok=True)
                d.chmod(0o777)

    build_application_images(compose_config)

    try:
        result = compose.up(capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start application: {result.stderr}")

        # Wait for services that expose ports — they must be reachable before tests run.
        # Services without ports (e.g. one-shot CLI workers) are skipped.
        port_services = [
            name
            for name, cfg in compose_config.get("services", {}).items()
            if cfg.get("ports")
        ]
        for service in port_services:
            compose.wait_for(service)
            try:
                compose.verify_health(service)
            except ValueError:
                pass  # No HEALTHCHECK in image; running state is sufficient
            except TimeoutError as e:
                logs = compose.logs(service)
                raise RuntimeError(
                    f"Service '{service}' did not become healthy.\n"
                    f"Logs:\n{logs}"
                ) from e

        # Fix permissions on volume mount directories after all entrypoints have
        # finished. Entrypoints run as a non-root user and create subdirectories
        # owned by that uid. chmod a+rwX makes them writable by the test runner
        # regardless of which uid it runs as.
        for service in compose_config.get("services", {}).values():
            for volume in service.get("volumes", []):
                host_path = volume.split(":")[0]
                if host_path.startswith("./") or host_path.startswith("../"):
                    subprocess.run(
                        ["docker", "run", "--rm", "-v", f"{app_dir / host_path}:/mount",
                         "alpine", "chmod", "-R", "a+rwX", "/mount"],
                        capture_output=True,
                    )
    except Exception:
        compose.down(capture_output=True)
        raise

    yield compose

    compose.down(capture_output=True)
