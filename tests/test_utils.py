import subprocess
import time
from pathlib import Path

import docker
import yaml

client = docker.from_env()


def _find_container(service_name, project=None):
    """Find a Docker container by service name, optionally scoped to a Compose project."""
    if project is not None:
        containers = client.containers.list(filters={
            "label": [
                f"com.docker.compose.project={project}",
                f"com.docker.compose.service={service_name}",
            ]
        })
        return containers[0] if containers else None
    return next((c for c in client.containers.list() if service_name in c.name), None)


def wait_for_service(service_name, timeout=60, project=None):
    """Wait until a Docker container is in running state."""
    start = time.time()
    while True:
        try:
            container = _find_container(service_name, project=project)
            if container is not None and container.status == 'running':
                return True
        except Exception:
            pass

        if time.time() - start > timeout:
            raise TimeoutError(f"Container {service_name} did not start within {timeout} seconds")

        time.sleep(1)


def container_is_running(service_name, project=None):
    """Check if a Docker container is running."""
    return _find_container(service_name, project=project) is not None


def verify_service_health(service_name, timeout=180, project=None):
    """Verify the health of a service container."""
    start = time.time()
    while True:
        container = _find_container(service_name, project=project)
        if container is None:
            raise ValueError(f"No running container found for service {service_name}")
        if 'Health' not in container.attrs['State']:
            raise ValueError(f"Container for service {service_name} does not have health status")

        health_status = container.attrs['State']['Health']['Status']
        if health_status == 'healthy':
            return True
        if time.time() - start > timeout:
            raise TimeoutError(f"Service {service_name} did not become healthy within {timeout} seconds")

        time.sleep(1)


def get_application_services(app_name):
    """Get the list of services defined in an application's docker-compose file."""
    compose_file = f"applications/{app_name}/docker-compose.yaml"
    try:
        with open(compose_file) as f:
            services = yaml.safe_load(f)['services'].keys()
    except FileNotFoundError:
        raise FileNotFoundError(f"Docker compose file for application {app_name} not found at {compose_file}")

    return services


class ComposeProject:
    """
    Wraps docker compose operations for a specific project.

    Ensures all commands use the correct --project-name so test containers
    never conflict with a running development stack.

    For component fixtures, `url` holds the HTTP base URL.
    For application fixtures, path-like access (via /) is relative to `app_dir`.
    """

    def __init__(
        self,
        project: str,
        compose_file: Path | None = None,
        app_dir: Path | None = None,
        url: str | None = None,
    ):
        self.project = project
        self.app_dir = app_dir
        self.url = url
        self._base_cmd = ["docker", "compose", "--project-name", project]
        if compose_file:
            self._base_cmd += ["-f", str(compose_file)]

    def _run(self, *args, **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault("cwd", self.app_dir)
        return subprocess.run([*self._base_cmd, *args], **kwargs)

    def build(self, *services, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose build."""
        return self._run("build", *services, **kwargs)

    def up(self, *services, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose up -d."""
        return self._run("up", "-d", *services, **kwargs)

    def down(self, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose down -v."""
        return self._run("down", "-v", **kwargs)

    def stop(self, *services, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose stop."""
        return self._run("stop", *services, **kwargs)

    def rm(self, *services, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose rm -f."""
        return self._run("rm", "-f", *services, **kwargs)

    def restart(self, service: str, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose restart for a single service."""
        return self._run("restart", service, **kwargs)

    def run(self, service: str, *args, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose run --rm (one-off command in a service container)."""
        return self._run("run", "--rm", service, *args, **kwargs)

    def logs(self, service: str) -> str:
        """Return combined stdout+stderr logs for a service."""
        result = self._run("logs", service, capture_output=True, text=True)
        return result.stdout + result.stderr

    def verify_health(self, service: str, timeout: int = 180) -> bool:
        """Wait for a service container's health check to pass."""
        return verify_service_health(service, timeout=timeout, project=self.project)

    def wait_for(self, service: str, timeout: int = 60) -> None:
        """Wait until a service container is in running state."""
        wait_for_service(service, timeout=timeout, project=self.project)

    def __truediv__(self, other):
        """Allow path-like operations relative to app_dir (e.g. compose / 'code' / 'parsers')."""
        return self.app_dir / other
