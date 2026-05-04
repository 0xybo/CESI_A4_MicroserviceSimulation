"""Docker-based platform implementation."""

from __future__ import annotations

import json
import socket
import shutil
import subprocess
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.Common.Monitor.default_monitor import DefaultMonitor
from src.Common.Platform import Platform
from src.Common.Utils.logger import get_logger
from src.Config import SimulationConfig, load_simulation_config

logger = get_logger(__name__)


class DockerPlatform(Platform):
    """Build and run the generated Docker architecture."""

    def __init__(self) -> None:
        super().__init__()
        self.docker_compose_path: Path | None = None
        self.results_dir: Path | None = None
        self.runtime_root: Path | None = None

    def get_platform_name(self) -> str:
        return "docker"

    def build(self, config_path: str | Path, output_dir: str | Path | None = None) -> None:
        output_root = Path(output_dir or ".output")
        output_root.mkdir(parents=True, exist_ok=True)

        config_path = Path(config_path)
        if not config_path.exists():
            raise RuntimeError(f"Configuration file not found: {config_path}")

        config = load_simulation_config(config_path)
        logger.info("Configuration loaded from %s", config_path)
        logger.info("Containers: %d", len(config.containers))
        logger.info("Services: %d", len(config.services))
        logger.info("Microservices: %d", len(config.microservices))

        runtime_root = output_root.resolve()
        runtime_root.mkdir(parents=True, exist_ok=True)
        self.runtime_root = runtime_root

        self._write_runtime_tree(runtime_root, config)
        self.docker_compose_path = runtime_root / "docker-compose.yml"
        logger.info("Docker runtime generated in %s", runtime_root.relative_to(Path.cwd()))

    def run(
        self,
        compose_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        detach: bool = True,
    ) -> None:
        """Run the most recent or explicitly provided Docker Compose file."""
        resolved_compose = self._resolve_compose_path(compose_path, output_dir).resolve()
        self._ensure_docker_daemon()

        command = self._compose_command()
        args = command + ["-f", str(resolved_compose), "up", "--build"]
        if detach:
            args.append("-d")

        # Log the command and working directory (relative) for debugging
        logger.info("Running compose file: %s", resolved_compose.relative_to(Path.cwd()))
        logger.info("Working directory: %s", resolved_compose.relative_to(Path.cwd()))
        try:
            completed = subprocess.run(
                args,
                check=True,
                cwd=str(resolved_compose.parent),
                capture_output=True,
                text=True,
            )
            logger.debug("Docker compose stdout: %s", completed.stdout)
            logger.debug("Docker compose stderr: %s", completed.stderr)
        except subprocess.CalledProcessError as exc:
            logger.debug("Docker compose stdout: %s", exc.stdout)
            logger.debug("Docker compose stderr: %s", exc.stderr)
            raise RuntimeError(
                f"Docker Compose failed to start the stack from {resolved_compose}:"
                f" {exc.stderr or exc}"
            ) from exc

    def test(
        self,
        compose_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        request_count: int | None = None,
    ) -> dict[str, Any]:
        """Run the generated architecture and collect request/resource metrics."""
        resolved_compose = self._resolve_compose_path(compose_path, output_dir).resolve()
        self._ensure_docker_daemon()

        runtime_root = resolved_compose.parent
        config = load_simulation_config(runtime_root / "config.json")
        effective_request_count = (
            request_count if request_count is not None else config.request_count
        )
        service_endpoints = self._load_runtime_service_endpoints(runtime_root)
        root_service_name = self._resolve_root_service_name(config)
        root_service_names = [root_service_name]
        if not root_service_names:
            raise RuntimeError("No root service found in configuration")
        root_service_endpoints = {
            service_name: service_endpoints[service_name]
            for service_name in root_service_names
            if service_name in service_endpoints
        }

        self.run(compose_path=resolved_compose, output_dir=output_dir, detach=True)
        self._wait_for_service_health(service_endpoints)

        monitor = DefaultMonitor(runtime_root / "result.csv")
        monitor.start_resource_monitor(
            lambda: self._collect_container_resource_usage(resolved_compose),
            interval_seconds=1.0,
        )

        try:
            # Submit all requests for all root services concurrently so they
            # are launched "at the same time". We create one task per
            # (service, request_index) pair and record durations as they
            # complete. The monitor is thread-safe.
            tasks: list[tuple[str, int]] = []
            for service_name in root_service_endpoints.keys():
                for request_index in range(1, effective_request_count + 1):
                    tasks.append((service_name, request_index))

            # max_workers = min(1000, len(tasks) or 1)
            max_workers = len(tasks) or 1

            # Create a synchronization event: all threads wait on this before sending
            start_event = Event()
            futures = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks first (they will wait on start_event before sending)
                for service_name, request_index in tasks:
                    service_url = root_service_endpoints[service_name]["url"]
                    logger.debug(
                        "Scheduling request %s for service %s",
                        request_index,
                        service_name,
                    )

                    def _send(service=service_name, idx=request_index, url=service_url):
                        # Wait for the signal to start sending all requests simultaneously
                        start_event.wait()

                        started = time.perf_counter()
                        try:
                            resp = self._post_json(
                                f"{url}/execute",
                                {
                                    "serviceName": service,
                                    "requestIndex": idx,
                                    "requestCount": effective_request_count,
                                },
                            )
                            duration_ms = (time.perf_counter() - started) * 1000
                            success = isinstance(resp, dict) and resp.get("status") == "ok"
                            monitor.record_request(
                                service_name=service,
                                request_index=idx,
                                request_duration_ms=duration_ms,
                                success=success,
                            )
                            logger.info(
                                "Completed %s request %s/%s in %.3f ms (mean duration %.3f ms, "
                                "mean resources %.3f%%)",
                                service,
                                idx,
                                effective_request_count,
                                duration_ms,
                                monitor.mean_request_duration_ms(),
                                monitor.mean_resource_usage_percent(),
                            )
                            return service, idx, resp
                        except Exception:  # pylint: disable=broad-exception-caught
                            duration_ms = (time.perf_counter() - started) * 1000
                            try:
                                monitor.record_request(
                                    service_name=service,
                                    request_index=idx,
                                    request_duration_ms=duration_ms,
                                    success=False,
                                )
                            except Exception:  # pylint: disable=broad-exception-caught
                                pass
                            raise

                    futures[executor.submit(_send)] = (service_name, request_index)

                # All tasks are now submitted and waiting. Signal them to start simultaneously.
                logger.info(
                    "All %d requests scheduled. Releasing threads to start sending...", len(tasks)
                )
                start_event.set()

                # Wait for futures and fail-fast on the first exception
                for future in as_completed(futures.keys()):
                    idx = futures[future][1]
                    try:
                        service, idx, response = future.result()
                        if isinstance(response, dict) and response.get("status") == "error":
                            raise RuntimeError(
                                f"Service {service} reported an error: "
                                f"{response.get('message', 'unknown error')}"
                            )
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        # Show error without traceback and print traceback at debug level
                        logger.error(
                            "Error during request %s for service %s: %s",
                            idx,
                            futures[future][0],
                            exc,
                        )
                        logger.debug("Exception details for request %s: ", idx, exc_info=True)

        finally:
            monitor.stop_resource_monitor()

        result_csv = monitor.export_to_csv(runtime_root / f"result_{effective_request_count}.csv")
        summary = monitor.summary()

        logger.info(
            "Test completed: mean request duration %.3f ms, mean resources %.3f%%, success: %.2f%%",
            summary["meanRequestDurationMs"],
            summary["meanResourceUsagePercent"],
            summary["successRate"] * 100,
        )

        return {
            "platform": self.get_platform_name(),
            "composePath": str(resolved_compose),
            "resultCsv": str(result_csv),
            "requestCount": effective_request_count,
            "services": root_service_names,
            "summary": summary,
        }

    def stop(
        self,
        compose_path: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        """Stop and remove the generated Docker Compose stack."""
        resolved_compose = self._resolve_compose_path(compose_path, output_dir).resolve()
        self._ensure_docker_daemon()

        command = self._compose_command()
        args = command + ["-f", str(resolved_compose), "down", "--remove-orphans"]

        logger.info("Stopping compose stack: %s", resolved_compose.relative_to(Path.cwd()))
        try:
            completed = subprocess.run(
                args,
                check=True,
                cwd=str(resolved_compose.parent),
                capture_output=True,
                text=True,
            )
            logger.debug("Docker compose stop stdout: %s", completed.stdout)
            logger.debug("Docker compose stop stderr: %s", completed.stderr)
        except subprocess.CalledProcessError as exc:
            logger.debug("Docker compose stop stdout: %s", exc.stdout)
            logger.debug("Docker compose stop stderr: %s", exc.stderr)
            raise RuntimeError(
                f"Docker Compose failed to stop the stack from {resolved_compose}:"
                f" {exc.stderr or exc}"
            ) from exc

    def execute(
        self,
        config_path: str,
        request_count: int,
        output_file: str | None = None,
        docker_compose_path: str | None = None,
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        _ = kwargs
        if docker_compose_path is None:
            self.build(config_path, output_dir)
            docker_compose_path = (
                str(self.docker_compose_path) if self.docker_compose_path else None
            )

        result = self.test(
            compose_path=docker_compose_path,
            output_dir=output_dir,
            request_count=request_count,
        )

        if output_file is not None:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

        return result

    def cleanup_runtime(self) -> None:
        """Clean up any generated runtime resources."""
        if self.docker_compose_path and self.docker_compose_path.exists():
            try:
                subprocess.run(
                    [*self._compose_command(), "-f", str(self.docker_compose_path), "down"],
                    check=False,
                    cwd=str(self.docker_compose_path.parent),
                    timeout=30,
                    capture_output=True,
                    text=True,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    @staticmethod
    def _ensure_docker_daemon() -> None:
        try:
            subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError(
                "Docker is installed but the daemon is not available. Start Docker Desktop or "
                "the Docker daemon and retry."
            ) from exc

    @staticmethod
    def _compose_command() -> list[str]:
        if shutil.which("docker") is not None:
            try:
                subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
                return ["docker", "compose"]
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        if shutil.which("docker-compose") is not None:
            return ["docker-compose"]

        raise RuntimeError("Neither 'docker compose' nor 'docker-compose' is available")

    def _resolve_compose_path(
        self,
        compose_path: str | Path | None,
        output_dir: str | Path | None,
    ) -> Path:
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

    @staticmethod
    def _allocate_free_port(used_ports: set[int]) -> int:
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                port = int(sock.getsockname()[1])
            if port not in used_ports:
                return port

    @staticmethod
    def _build_service_runtime_config(
        container_name: str,
        service_name: str,
        service_config: Any,
        microservices_config: dict[str, Any],
        port: int,
    ) -> dict[str, Any]:
        service_data = (
            service_config.model_dump(by_alias=True) if service_config is not None else {}
        )
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

    def _write_runtime_tree(self, runtime_root: Path, config: SimulationConfig) -> None:
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
                port = self._allocate_free_port(used_ports)
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
            self._render_docker_compose(compose_services),
            encoding="utf-8",
        )

    # NOTE: renderer methods for generating service/microservice/container
    # scripts as strings have been removed. The build now copies the
    # real Python files from `src/Common/{Container,Service,Microservice}`
    # into the runtime output tree so the runtime uses actual files.

    @staticmethod
    def _render_docker_compose(services: dict[str, dict[str, Any]]) -> str:
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

    def _load_runtime_service_endpoints(self, runtime_root: Path) -> dict[str, dict[str, Any]]:
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
            container_configs[container_dir.name] = json.loads(
                config_path.read_text(encoding="utf-8")
            )

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

    @staticmethod
    def _resolve_root_service_name(config: SimulationConfig) -> str:
        if config.entrypoint and config.entrypoint in config.services:
            return config.entrypoint

        for service_name, service_config in config.services.items():
            if service_config.entrypoint == "A":
                return service_name

        if "ServiceA" in config.services:
            return "ServiceA"

        return next(iter(config.services))

    def _wait_for_service_health(
        self,
        service_endpoints: dict[str, dict[str, Any]],
        timeout_seconds: float = 120.0,
    ) -> None:
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

    @staticmethod
    def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
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

    def _collect_container_resource_usage(self, compose_path: Path) -> float:
        command = self._compose_command()
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
