import os
import socket
import subprocess
import time
from pathlib import Path

import docker

client = docker.from_env()


def find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def assign_ports(*env_var_names: str) -> dict[str, str]:
    """Return a mapping of env var names to free port strings.

    The first entry is treated as the primary HTTP port by ``component_endpoint``.
    """
    return {name: str(find_free_port()) for name in env_var_names}


class ComposeProject:
    """
    Wraps docker compose operations for a specific project.

    Ensures all commands use the correct --project-name so test containers
    never conflict with a running development stack.

    For component fixtures, `url` holds the HTTP base URL.
    For application fixtures, path-like access (via /) is relative to `app_dir`.

    `compose_env` provides extra environment variables substituted by docker compose
    (e.g. port overrides).  They are merged with the current process environment so
    the docker binary itself is still on PATH.
    """

    def __init__(
        self,
        project: str,
        compose_file: Path | None = None,
        app_dir: Path | None = None,
        url: str | None = None,
        compose_env: dict | None = None,
    ):
        self.project = project
        self.app_dir = app_dir
        self.url = url
        self._compose_env = compose_env or {}
        self._base_cmd = ["docker", "compose", "--project-name", project]
        if compose_file:
            self._base_cmd += ["-f", str(compose_file)]

    def _run(self, *args, **kwargs) -> subprocess.CompletedProcess:
        kwargs.setdefault("cwd", self.app_dir)
        if self._compose_env:
            base_env = kwargs.pop("env", os.environ)
            kwargs["env"] = {**base_env, **self._compose_env}
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

    def exec(self, service: str, *args, env: dict | None = None, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose exec -T (non-interactive) in a running container."""
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        cmd = ["exec", "-T"]
        for k, v in (env or {}).items():
            cmd += ["-e", f"{k}={v}"]
        cmd += [service, *args]
        return self._run(*cmd, **kwargs)

    def cp(self, src: str, dst: str, **kwargs) -> subprocess.CompletedProcess:
        """Run docker compose cp."""
        return self._run("cp", src, dst, **kwargs)

    def logs(self, service: str) -> str:
        """Return combined stdout+stderr logs for a service."""
        result = self._run("logs", service, capture_output=True, text=True)
        return result.stdout + result.stderr

    def _get_container(self, service: str):
        """Return the Docker container for a service by matching its Compose name prefix.

        Docker Compose names containers as {project}-{service}-{n}. We match by prefix
        so that any replica index is accepted.
        """
        prefix = f"{self.project}-{service}-"
        containers = [c for c in client.containers.list(all=True) if c.name.startswith(prefix)]
        return containers[0] if containers else None

    def verify_health(self, service: str, timeout: int = 180) -> bool:
        """Wait for a service container's health check to pass."""
        start = time.time()
        while True:
            container = self._get_container(service)
            if container is None:
                raise ValueError(f"No container found for service {service}")
            container.reload()
            if 'Health' not in container.attrs['State']:
                raise ValueError(f"Container for service {service} does not have health status")
            if container.attrs['State']['Health']['Status'] == 'healthy':
                return True
            if time.time() - start > timeout:
                raise TimeoutError(f"Service {service} did not become healthy within {timeout} seconds")
            time.sleep(1)

    def wait_for(self, service: str, timeout: int = 60) -> None:
        """Wait until a service container is in running state."""
        start = time.time()
        while True:
            container = self._get_container(service)
            if container is not None:
                container.reload()
                if container.status == 'running':
                    return
            if time.time() - start > timeout:
                raise TimeoutError(f"Container {service} did not start within {timeout} seconds")
            time.sleep(1)

    def __truediv__(self, other):
        """Allow path-like operations relative to app_dir (e.g. compose / 'code' / 'parsers')."""
        return self.app_dir / other
