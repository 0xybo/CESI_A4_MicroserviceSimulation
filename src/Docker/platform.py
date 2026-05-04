"""Docker-based platform implementation."""

from __future__ import annotations

import json
import subprocess
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from typing import Any

from src.Common.Monitor.default_monitor import DefaultMonitor
from src.Common.Platform import Platform
from src.Common.Utils.logger import get_logger
from src.Config import SimulationConfig, load_simulation_config
from src.Docker.platform_docker import (
    ensure_docker_daemon,
    get_compose_command,
    post_json,
    collect_container_resource_usage,
)
from src.Docker.platform_runtime import (
    resolve_compose_path,
    build_service_runtime_config,
    write_runtime_tree,
    load_runtime_service_endpoints,
    resolve_root_service_name,
    wait_for_service_health,
)

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

        write_runtime_tree(runtime_root, config)
        self.docker_compose_path = runtime_root / "docker-compose.yml"
        logger.info("Docker runtime generated in %s", runtime_root.relative_to(Path.cwd()))

    def run(
        self,
        compose_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        detach: bool = True,
    ) -> None:
        """Run the most recent or explicitly provided Docker Compose file."""
        resolved_compose = resolve_compose_path(compose_path, output_dir).resolve()
        ensure_docker_daemon()

        command = get_compose_command()
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
        resolved_compose = resolve_compose_path(compose_path, output_dir).resolve()
        ensure_docker_daemon()

        runtime_root = resolved_compose.parent
        config = load_simulation_config(runtime_root / "config.json")
        effective_request_count = (
            request_count if request_count is not None else config.request_count
        )
        service_endpoints = load_runtime_service_endpoints(runtime_root)
        root_service_name = resolve_root_service_name(config)
        root_service_names = [root_service_name]
        if not root_service_names:
            raise RuntimeError("No root service found in configuration")
        root_service_endpoints = {
            service_name: service_endpoints[service_name]
            for service_name in root_service_names
            if service_name in service_endpoints
        }

        self.run(compose_path=resolved_compose, output_dir=output_dir, detach=True)
        wait_for_service_health(service_endpoints)

        monitor = DefaultMonitor(runtime_root / "result.csv")
        monitor.start_resource_monitor(
            lambda: collect_container_resource_usage(resolved_compose),
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
                            resp = post_json(
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
        resolved_compose = resolve_compose_path(compose_path, output_dir).resolve()
        ensure_docker_daemon()

        command = get_compose_command()
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
                    [*get_compose_command(), "-f", str(self.docker_compose_path), "down"],
                    check=False,
                    cwd=str(self.docker_compose_path.parent),
                    timeout=30,
                    capture_output=True,
                    text=True,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # NOTE: Helper methods have been extracted to separate modules:
    # - platform_docker.py: Docker CLI operations
    # - platform_runtime.py: Runtime configuration and generation
