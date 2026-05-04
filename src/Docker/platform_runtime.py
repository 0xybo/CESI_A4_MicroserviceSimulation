"""Docker runtime generation and configuration utilities."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from src.Common.Utils.logger import get_logger
from src.Config import SimulationConfig, load_simulation_config
from src.Docker.platform_docker import get_compose_command, allocate_free_port

logger = get_logger(__name__)


def resolve_compose_path(
    compose_path: str | Path | None,
    output_dir: str | Path | None,
) -> Path:
    """Resolve a docker-compose.yml path using standard search rules."""
    if compose_path is not None:
        resolved = Path(compose_path)
        if resolved.is_dir():
            resolved = resolved / "docker-compose.yml"
        if not resolved.exists():
            raise RuntimeError(f"Compose file not found: {resolved}")
        return resolved.resolve()

    search_root = Path(output_dir or ".output")
    if not search_root.exists():
        raise RuntimeError(f"Output directory not found: {search_root}")

    direct_compose = search_root / "docker-compose.yml"
    if direct_compose.exists():
        return direct_compose.resolve()

    candidates = sorted(
        search_root.glob("*/docker-compose.yml"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise RuntimeError(f"No docker-compose.yml found under {search_root}")
    return candidates[-1].resolve()


def build_service_runtime_config(
    container_name: str,
    service_name: str,
    service_config: Any,
    microservices_config: dict[str, Any],
    port: int,
) -> dict[str, Any]:
    """Build runtime configuration dict for a service."""
    service_data = service_config.model_dump(by_alias=True) if service_config is not None else {}
    service_data.update(
        {
            "containerName": container_name,
            "serviceName": service_name,
            "port": port,
            "host": "0.0.0.0",
            "microservices": {},
        }
    )

    if service_config is not None and hasattr(service_config, "microservices"):
        service_microservices: dict[str, Any] = {}
        for microservice_name in service_config.microservices.keys():
            microservice_config = microservices_config.get(microservice_name)
            if microservice_config is not None:
                service_microservices[microservice_name] = microservice_config.model_dump(
                    by_alias=True
                )
        service_data["microservices"] = service_microservices

    return service_data


def write_runtime_tree(runtime_root: Path, config: SimulationConfig) -> dict[str, dict[str, Any]]:
    """Generate Docker runtime directory structure and return service endpoints."""
    runtime_config = config.model_dump(by_alias=True)
    runtime_config["name"] = runtime_root.name

    used_ports: set[int] = set()
    compose_services: dict[str, dict[str, Any]] = {}
    runtime_service_endpoints: dict[str, dict[str, Any]] = {}

    # Project root to locate source templates and copy src folder
    project_root = Path(__file__).resolve().parent.parent.parent

    # Copy entire src folder (not symlink) so imports work in Docker container
    src_dest = runtime_root / "src"
    if src_dest.exists():
        shutil.rmtree(str(src_dest))
    shutil.copytree(str(project_root / "src"), str(src_dest))

    # Copy requirements.txt to runtime root
    requirements_src = project_root / "requirements.txt"
    if requirements_src.exists():
        shutil.copy(str(requirements_src), str(runtime_root / "requirements.txt"))

    # Copy runtime_runner.py into the generated folder
    runtime_runner_src = project_root / "src" / "Docker" / "runtime_runner.py"
    if runtime_runner_src.exists():
        shutil.copy(str(runtime_runner_src), str(runtime_root / "runtime_runner.py"))

    # Create Dockerfile for building containers with dependencies
    dockerfile_content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
"""
    (runtime_root / "Dockerfile").write_text(dockerfile_content, encoding="utf-8")

    for container_name, container_config in config.containers.items():
        service_ports: list[int] = []

        for service_name in container_config.services.keys():
            port = allocate_free_port(used_ports)
            used_ports.add(port)
            service_ports.append(port)

            runtime_service_endpoints[service_name] = {
                "container": container_name,
                "port": port,
                "url": f"http://127.0.0.1:{port}",
            }

        compose_services[container_name] = {
            "build": {
                "context": ".",
                "dockerfile": "Dockerfile",
            },
            "image": container_name.lower(),
            "cpus": container_config.cpu_limit,
            "working_dir": "/app",
            "command": [
                "python",
                "runtime_runner.py",
                "--config",
                "/app/config.json",
                "--container",
                container_name,
            ],
            "environment": {
                "PYTHONUNBUFFERED": "1",
                "PYTHONPATH": "/app",
            },
            "volumes": [
                "./:/app",
            ],
            "ports": [f"{port}:{port}" for port in service_ports],
            "networks": ["simulation"],
            "restart": "unless-stopped",
        }

    runtime_config["runtimeServiceEndpoints"] = runtime_service_endpoints
    (runtime_root / "config.json").write_text(
        json.dumps(runtime_config, indent=2) + "\n",
        encoding="utf-8",
    )

    (runtime_root / "docker-compose.yml").write_text(
        render_docker_compose(compose_services),
        encoding="utf-8",
    )

    return runtime_service_endpoints


def render_docker_compose(services: dict[str, dict[str, Any]]) -> str:
    """Render docker-compose.yml content from service definitions."""
    lines: list[str] = ["services:"]
    for container_name, service_data in services.items():
        lines.append(f"  {container_name}:")

        # Render build section if present
        if "build" in service_data:
            lines.append("    build:")
            for build_key, build_value in service_data["build"].items():
                lines.append(f"      {build_key}: {json.dumps(build_value)}")

        # Render image (for build output or fallback)
        if "image" in service_data:
            lines.append(f"    image: {json.dumps(service_data['image'])}")
        if "working_dir" in service_data:
            lines.append(f"    working_dir: {json.dumps(service_data['working_dir'])}")
        if "command" in service_data:
            lines.append(f"    command: {json.dumps(service_data['command'])}")
        if "cpus" in service_data:
            lines.append(f"    cpus: {json.dumps(service_data['cpus'])}")
        lines.append("    environment:")
        for key, value in service_data["environment"].items():
            lines.append(f"      {key}: {json.dumps(value)}")
        lines.append("    volumes:")
        for volume in service_data["volumes"]:
            lines.append(f"      - {json.dumps(volume)}")
        lines.append("    ports:")
        for port in service_data["ports"]:
            lines.append(f"      - {json.dumps(port)}")
        lines.append("    networks:")
        for network in service_data["networks"]:
            lines.append(f"      - {json.dumps(network)}")
        lines.append(f"    restart: {json.dumps(service_data['restart'])}")

    lines.extend(["networks:", "  simulation:", "    driver: bridge"])
    return "\n".join(lines) + "\n"


def load_runtime_service_endpoints(runtime_root: Path) -> dict[str, dict[str, Any]]:
    """Load service endpoints from runtime configuration."""
    config_file = runtime_root / "config.json"
    config_data = json.loads(config_file.read_text(encoding="utf-8"))

    runtime_endpoints = config_data.get("runtimeServiceEndpoints", {})
    if isinstance(runtime_endpoints, dict) and runtime_endpoints:
        return {
            service_name: {
                "container": str(service_data["container"]),
                "port": int(service_data["port"]),
                "url": str(
                    service_data.get("url") or f"http://127.0.0.1:{int(service_data['port'])}"
                ),
            }
            for service_name, service_data in runtime_endpoints.items()
        }

    validated_config = load_simulation_config(config_file).model_dump(by_alias=True)
    endpoints: dict[str, dict[str, Any]] = {}

    containers_dir = runtime_root / "containers"
    if not containers_dir.exists():
        return endpoints

    container_configs: dict[str, dict[str, Any]] = {}
    for container_dir in sorted(path for path in containers_dir.iterdir() if path.is_dir()):
        config_path = container_dir / "config.json"
        if not config_path.exists():
            continue
        container_configs[container_dir.name] = json.loads(config_path.read_text(encoding="utf-8"))

    service_names = list(validated_config.get("services", {}).keys())

    for service_name in service_names:
        for container_name, container_config in container_configs.items():
            runtime_services = container_config.get("runtimeServices", {})
            service_data = runtime_services.get(service_name)
            if service_data is None:
                continue
            port = int(service_data["port"])
            endpoints[service_name] = {
                "container": container_name,
                "port": port,
                "url": f"http://127.0.0.1:{port}",
            }
            break

    if len(endpoints) != len(service_names):
        missing_services = [name for name in service_names if name not in endpoints]
        raise RuntimeError(f"Missing runtime endpoints for services: {missing_services}")

    return endpoints


def resolve_root_service_name(config: SimulationConfig) -> str:
    """Determine the root/entry service from config."""
    if config.entrypoint and config.entrypoint in config.services:
        return config.entrypoint

    for service_name, service_config in config.services.items():
        if service_config.entrypoint == "A":
            return service_name

    if "ServiceA" in config.services:
        return "ServiceA"

    return next(iter(config.services))


def wait_for_service_health(
    service_endpoints: dict[str, dict[str, Any]],
    timeout_seconds: float = 120.0,
) -> None:
    """Wait for all services to become healthy."""
    deadline = time.monotonic() + timeout_seconds
    pending = set(service_endpoints.keys())

    while pending:
        for service_name in list(pending):
            service_url = f'{service_endpoints[service_name]["url"]}/health'
            try:
                with urlopen(service_url, timeout=5):
                    pending.remove(service_name)
            except Exception:  # pylint: disable=broad-exception-caught
                continue

        if not pending:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(
                f"Timed out waiting for services to become healthy: {sorted(pending)}"
            )
        time.sleep(1.0)
