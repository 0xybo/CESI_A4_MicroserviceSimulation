"""Runtime HTTP runner used by generated Docker containers."""

from __future__ import annotations

import argparse
from http.client import RemoteDisconnected
import json
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import traceback

from src.Common.Microservice.context import ExecutionContext
from src.Common.Microservice.microservice import Microservice
from src.Common.Service.service import Service
from src.Common.Service.result import ServiceRunResult
from src.Common.Utils.logger import get_logger
from src.Config import load_simulation_config

logger = get_logger(__name__)


class _ServiceRuntime:
    def __init__(self, service_name: str, service: Service, context: ExecutionContext) -> None:
        self.service_name = service_name
        self.service = service
        self.context = context

    def execute_once(self, microservice_name: str | None = None) -> dict[str, Any]:
        """Execute the service once and return a result dictionary."""
        try:
            result = self.service.execute(
                self.context,
                request_count=1,
                microservice_name=microservice_name,
            )
            success = result.failures == 0
            return {
                "service": self.service_name,
                "status": "ok" if success else "error",
                "calls": result.calls,
                "success": result.success,
                "failures": result.failures,
            }
        except (
            Exception  # pylint: disable=broad-exception-caught
        ) as exc:  # capture unexpected errors during execution
            tb = traceback.format_exc()
            logger.exception("Service %s execution raised an exception", self.service_name)
            return {
                "service": self.service_name,
                "status": "error",
                "calls": 0,
                "success": 0,
                "failures": 1,
                "message": str(exc),
                "traceback": tb,
            }


class _ServiceProxy:
    def __init__(self, service_name: str, service_url: str) -> None:
        self.service_name = service_name
        self.service_url = service_url.rstrip("/")

    def execute(
        self,
        _context: ExecutionContext,
        request_count: int,
        microservice_name: str | None = None,
    ) -> ServiceRunResult:
        """Execute the service by making HTTP requests to its /execute endpoint."""
        success = 0
        failures = 0
        max_attempts = 3

        for request_index in range(1, request_count + 1):
            payload = {
                "serviceName": self.service_name,
                "requestIndex": request_index,
                "requestCount": request_count,
            }
            if microservice_name is not None:
                payload["microserviceName"] = microservice_name
            request = Request(
                f"{self.service_url}/execute",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            response_data: dict[str, Any] | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    with urlopen(request, timeout=300) as response:
                        body = response.read().decode("utf-8")
                        response_data = json.loads(body or "{}")
                    break
                except HTTPError as exc:
                    error_body = exc.read().decode("utf-8") if exc.fp is not None else ""
                    if exc.code >= 500 and (
                        "Connection reset by peer" in error_body
                        or "ConnectionResetError" in error_body
                    ):
                        if attempt < max_attempts:
                            logger.warning(
                                "Dependency service %s returned transient %s on attempt %d/%d; retrying",
                                self.service_name,
                                exc.code,
                                attempt,
                                max_attempts,
                            )
                            time.sleep(0.1 * attempt)
                            continue
                    logger.error(
                        "Dependency service %s failed with status %s: %s",
                        self.service_name,
                        exc.code,
                        error_body or exc.reason,
                    )
                    failures += 1
                    break
                except (
                    ConnectionResetError,
                    RemoteDisconnected,
                    TimeoutError,
                    URLError,
                    OSError,
                ) as exc:
                    if attempt < max_attempts:
                        logger.warning(
                            "Dependency service %s request failed on attempt %d/%d: %s",
                            self.service_name,
                            attempt,
                            max_attempts,
                            exc,
                        )
                        time.sleep(0.1 * attempt)
                        continue
                    logger.error(
                        "Dependency service %s request failed: %s",
                        self.service_name,
                        exc,
                    )
                    failures += 1
                    break

            if response_data is None:
                continue
            if response_data.get("status") == "ok":
                success += 1
            else:
                failures += 1
                logger.debug(
                    "Dependency service %s returned error payload: %s",
                    self.service_name,
                    response_data,
                )

        return ServiceRunResult(
            service_name=self.service_name,
            calls=request_count,
            success=success,
            failures=failures,
        )


class _BaseServiceHandler(BaseHTTPRequestHandler):
    """Base HTTP handler for service endpoints, to be extended with a runtime instance."""

    runtime: _ServiceRuntime

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests for health checks."""
        if self.path != "/health":
            self._write_json(404, {"error": "not found"})
            return
        self._write_json(200, {"service": self.runtime.service_name, "status": "healthy"})

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests for service execution."""
        if self.path != "/execute":
            self._write_json(404, {"error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload: dict[str, Any] = {}
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                payload = json.loads(raw_body)

            requested_service = payload.get("serviceName")
            if requested_service is not None and requested_service != self.runtime.service_name:
                self._write_json(
                    400,
                    {
                        "error": "service mismatch",
                        "service": self.runtime.service_name,
                        "requestedService": requested_service,
                    },
                )
                return

            microservice_name = payload.get("microserviceName")

            execution_result = self.runtime.execute_once(microservice_name=microservice_name)
            status_code = 200 if execution_result.get("status") == "ok" else 500
            self._write_json(status_code, execution_result)
        except (
            Exception  # pylint: disable=broad-exception-caught
        ):  # fallback: log and return error with traceback
            tb = traceback.format_exc()
            logger.exception(
                "Unhandled exception while handling /execute for %s", self.runtime.service_name
            )
            self._write_json(
                500,
                {
                    "service": self.runtime.service_name,
                    "status": "error",
                    "message": "unhandled exception",
                    "traceback": tb,
                },
            )

    def log_message(self, format: str, *args: Any) -> None:  # pylint: disable=redefined-builtin
        _ = format
        _ = args

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        """Helper method to write a JSON response with the given status code and payload."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _create_handler(runtime: _ServiceRuntime) -> type[_BaseServiceHandler]:
    class ServiceHandler(_BaseServiceHandler):
        """HTTP handler class for the service, with a bound runtime instance."""

    ServiceHandler.runtime = runtime
    return ServiceHandler


def _build_runtime(
    config_path: Path, container_name: str
) -> list[tuple[str, int, _ServiceRuntime]]:
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    runtime_endpoints = config_data.get("runtimeServiceEndpoints", {})
    config = load_simulation_config(config_path)

    if container_name not in config.containers:
        raise RuntimeError(f"Unknown container '{container_name}'")

    container_config = config.containers[container_name]
    microservice_configs = dict(config.microservices)
    service_configs = dict(config.services)

    microservices = {
        name: Microservice(name, microservice_config)
        for name, microservice_config in microservice_configs.items()
    }

    service_owners = {
        microservice_name: service_name
        for service_name, service_config in service_configs.items()
        for microservice_name in service_config.microservices.keys()
    }

    # Build mapping from service_name to container_name for Docker internal connectivity
    service_to_container: dict[str, str] = {}
    for cont_name, cont_config in dict(config.containers).items():
        for svc_name in cont_config.services.keys():
            service_to_container[svc_name] = cont_name

    # Convert URLs for Docker internal connectivity (use container names instead of 127.0.0.1)
    service_proxies = {}
    for service_name, endpoint_config in runtime_endpoints.items():
        url = endpoint_config["url"]
        # Replace 127.0.0.1 with container name for internal Docker connectivity
        if service_name in service_to_container:
            container_for_service = service_to_container[service_name]
            port = endpoint_config["port"]
            url = f"http://{container_for_service}:{port}"
            logger.debug(
                "Service %s: using Docker internal URL %s (original: %s)",
                service_name,
                url,
                endpoint_config["url"],
            )
        service_proxies[service_name] = _ServiceProxy(service_name, url)

    context = ExecutionContext(
        microservices=microservices,
        services=service_proxies,
        service_owners=service_owners,
    )

    runtimes: list[tuple[str, int, _ServiceRuntime]] = []
    for service_name in container_config.services.keys():
        if service_name not in service_configs:
            raise RuntimeError(
                f"Service '{service_name}' referenced by container '{container_name}' is missing"
            )

        endpoint_config = runtime_endpoints.get(service_name)
        if endpoint_config is None:
            raise RuntimeError(
                f"Missing runtime endpoint configuration for service '{service_name}'"
            )

        port = int(endpoint_config["port"])
        service = Service(service_name, service_configs[service_name])
        runtimes.append((service_name, port, _ServiceRuntime(service_name, service, context)))

    if not runtimes:
        raise RuntimeError(f"Container '{container_name}' has no runnable services")

    return runtimes


def _start_service_server(
    service_name: str, port: int, runtime: _ServiceRuntime
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    handler = _create_handler(runtime)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Service %s listening on port %s", service_name, port)
    return server, thread


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runtime runner for generated Docker containers")
    parser.add_argument("--config", type=Path, required=True, help="Path to generated config.json")
    parser.add_argument("--container", required=True, help="Container name to run")
    return parser.parse_args()


def main() -> int:
    """Main entry point for the runtime runner."""
    args = _parse_args()
    runtimes = _build_runtime(args.config, args.container)

    servers: list[ThreadingHTTPServer] = []
    for service_name, port, runtime in runtimes:
        server, _ = _start_service_server(service_name, port, runtime)
        servers.append(server)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stopping runtime runner for container %s", args.container)
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
