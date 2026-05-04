"""Docker CLI and utility operations for platform execution."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def ensure_docker_daemon() -> None:
    """Verify Docker daemon is running."""
    try:
        subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(
            "Docker is installed but the daemon is not available. Start Docker Desktop or "
            "the Docker daemon and retry."
        ) from exc


def get_compose_command() -> list[str]:
    """Get the appropriate docker compose command."""
    if shutil.which("docker") is not None:
        try:
            subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
            return ["docker", "compose"]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    if shutil.which("docker-compose") is not None:
        return ["docker-compose"]

    raise RuntimeError("Neither 'docker compose' nor 'docker-compose' is available")


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to a service endpoint."""
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=300) as response:
            body = response.read().decode("utf-8")
            return json.loads(body or "{}")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp is not None else ""
        logger.error(
            "HTTP error from %s: status=%s body=%s",
            url,
            exc.code,
            error_body or exc.reason,
        )
        raise RuntimeError(
            f"Request failed for {url} with status {exc.code}: {error_body or exc.reason}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc.reason}") from exc


def collect_container_resource_usage(compose_path: Path) -> float:
    """Collect CPU resource usage from all containers in compose stack."""
    command = get_compose_command()
    try:
        ps_result = subprocess.run(
            command + ["-f", str(compose_path), "ps", "-q"],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(compose_path.parent),
        )
    except subprocess.CalledProcessError:
        return 0.0

    container_ids = [line.strip() for line in ps_result.stdout.splitlines() if line.strip()]
    if not container_ids:
        return 0.0

    stats_result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}", *container_ids],
        check=True,
        capture_output=True,
        text=True,
    )

    resource_values: list[float] = []
    for line in stats_result.stdout.splitlines():
        cleaned_line = line.strip().replace("%", "")
        if not cleaned_line:
            continue
        try:
            resource_values.append(float(cleaned_line))
        except ValueError:
            continue

    if not resource_values:
        return 0.0
    return sum(resource_values)


def allocate_free_port(used_ports: set[int]) -> int:
    """Allocate a free local port."""
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = int(sock.getsockname()[1])
        if port not in used_ports:
            return port
