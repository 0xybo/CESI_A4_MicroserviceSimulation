"""Python thread-based platform implementation.

Provides a Platform implementation that executes simulations using Python's
ThreadPoolExecutor for parallel container execution.
"""

from __future__ import annotations

import concurrent.futures
import json
import sys
import time
from pathlib import Path
from typing import Any

from src.Common.Platform import Platform
from src.Common.Container.container import Container
from src.Common.Microservice.microservice import Microservice
from src.Common.Microservice.context import ExecutionContext
from src.Common.Service.service import Service
from src.Common.Utils.logger import get_logger
from src.Config import SimulationConfig, load_simulation_config

logger = get_logger(__name__)

# Access ThreadPoolExecutor through module to avoid false linter positives
ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor
as_completed = concurrent.futures.as_completed


class PythonPlatform(Platform):
    """Platform implementation for Python thread-based execution.

    Executes microservice simulations using Python's ThreadPoolExecutor,
    allowing parallel container execution via worker threads.
    """

    def get_platform_name(self) -> str:
        """Get the platform name.

        Returns:
            "python"
        """
        return "python"

    def build(self, config_path: str, output_dir: str | None = None) -> None:
        """Build and validate the Python execution environment.

        Validates Python version, required dependencies (pydantic),
        configuration file existence, and creates timestamped test directory.

        Args:
            config_path: Path to simulation configuration.
            output_dir: Base output directory (default: .output).

        Raises:
            RuntimeError: If environment validation fails.
        """
        if output_dir is None:
            output_dir = ".output"

        config_path = Path(config_path)

        # Check Python version
        if sys.version_info < (3, 9):
            raise RuntimeError(
                f"Python 3.9+ required (current: {sys.version_info.major}.{sys.version_info.minor})"
            )

        # Check config file exists
        if not config_path.exists():
            raise RuntimeError(f"Configuration file not found: {config_path}")

        # Validate config file
        try:
            config = load_simulation_config(config_path)
            logger.info("Configuration valid: %s", config_path)
            logger.info("Containers: %d", len(config.containers))
            logger.info("Services: %d", len(config.services))
            logger.info("Microservices: %d", len(config.microservices))
        except Exception as e:
            raise RuntimeError(f"Failed to validate configuration: {e}") from e

        # Initialize test output manager
        test_dir = self.initialize_output_manager(output_dir)
        self.output_manager.save_config(config)
        logger.info("Test directory created: %s", test_dir)

    def execute(
        self,
        config_path: str,
        request_count: int,
        output_file: str | None = None,
        workers: int = 1,
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the simulation using Python threads.

        Creates per-service execution scripts and stores them in the test directory.
        Results and metrics are saved to the timestamped test output directory.

        Args:
            config_path: Path to simulation configuration.
            request_count: Number of requests per service.
            output_file: Optional path to write results (overrides default).
            workers: Number of worker threads (default: 1).
            output_dir: Base output directory (default: .output).
            **kwargs: Additional arguments (unused).

        Returns:
            Execution results dictionary.

        Raises:
            RuntimeError: If execution fails.
        """
        logger.info(
            "Starting simulation execution: config=%s, requests=%s, workers=%s",
            config_path,
            request_count,
            workers,
        )
        if output_dir is None:
            output_dir = ".output"
            logger.debug("Using default output directory: .output")

        self.record_timing()

        try:
            config_path = Path(config_path)
            logger.debug("Loading simulation configuration from: %s", config_path)
            config = load_simulation_config(config_path)
            logger.info(
                "Configuration loaded: containers=%d, services=%d, microservices=%d",
                len(config.containers),
                len(config.services),
                len(config.microservices),
            )

            # Initialize test output if not already done
            if self.output_manager is None:
                logger.debug("Initializing output manager")
                self.initialize_output_manager(output_dir)
                self.output_manager.save_config(config)

            logger.debug("Building runtime objects")
            microservices, services, containers = self._build_runtime(config)
            logger.debug(
                "Runtime built: microservices=%d, containers=%d",
                len(microservices),
                len(containers),
            )

            containers_config = dict(config.containers)
            root_service_name = self._resolve_root_service_name(config)
            root_service_names = [root_service_name]
            service_owners = self._build_service_owners(config)
            root_container_names = [
                container_name
                for container_name, container_config in containers_config.items()
                if any(
                    service_name in root_service_names for service_name in container_config.services
                )
            ]

            # Generate per-service scripts for each container
            logger.debug("Generating per-service scripts")
            self._generate_service_scripts(config, containers)

            run_started_at = time.perf_counter()
            logger.info(
                "Executing %d root container(s) with %d worker(s)",
                len(root_container_names),
                workers,
            )

            root_containers = {
                name: containers[name] for name in root_container_names if name in containers
            }

            if workers <= 1:
                logger.debug("Running containers sequentially")
                container_results = [
                    self._run_single_container(
                        container,
                        microservices,
                        services,
                        service_owners,
                        request_count,
                        root_service_name,
                    )
                    for container in root_containers.values()
                ]
            else:
                logger.debug("Running containers in parallel with %d workers", workers)
                container_results = []
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [
                        executor.submit(
                            self._run_single_container,
                            container,
                            microservices,
                            services,
                            service_owners,
                            request_count,
                            root_service_name,
                        )
                        for container in root_containers.values()
                    ]
                    for future in as_completed(futures):
                        container_results.append(future.result())

            total_elapsed_ms = (time.perf_counter() - run_started_at) * 1000
            logger.info("Simulation execution completed in %.2fms", total_elapsed_ms)

            results = {
                "platform": self.get_platform_name(),
                "config": str(config_path),
                "requestCount": request_count,
                "workers": workers,
                "totalElapsedMs": round(total_elapsed_ms, 3),
                "containers": sorted(container_results, key=lambda item: item["container"]),
            }

            # Save results to test directory
            logger.debug("Saving execution results")
            if self.output_manager is not None:
                results_path = self.output_manager.save_results(results)
                logger.info("Results saved to: %s", results_path)
            elif output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                logger.info("Results saved to: %s", output_path)
            else:
                # Default to .output folder if no output file specified
                output_path_dir = Path(output_dir)
                output_path_dir.mkdir(parents=True, exist_ok=True)
                default_output = output_path_dir / "python_simulation_results.json"
                default_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                logger.info("Results saved to: %s", default_output)

            self.complete_timing()
            return results

        except Exception as e:
            logger.error("Simulation execution failed: %s", e, exc_info=True)
            self.complete_timing()
            raise RuntimeError(f"Simulation execution failed: {e}") from e

    @staticmethod
    def _build_runtime(
        config: SimulationConfig,
    ) -> tuple[dict[str, Microservice], dict[str, Service], dict[str, Container]]:
        """Build runtime objects from simulation configuration.

        Args:
            config: Parsed simulation configuration.

        Returns:
            Tuple of (microservices, services, containers) dictionaries.
        """
        microservices = {
            name: Microservice(name, ms_config) for name, ms_config in config.microservices.items()
        }

        services = {
            name: Service(name, service_config) for name, service_config in config.services.items()
        }

        containers = {
            name: Container(name, container_config, services)
            for name, container_config in config.containers.items()
        }

        return microservices, services, containers

    @staticmethod
    def _build_service_owners(config: SimulationConfig) -> dict[str, str]:
        return {
            microservice_name: service_name
            for service_name, service_config in config.services.items()
            for microservice_name in service_config.microservices.keys()
        }

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

    def _generate_service_scripts(
        self, config: SimulationConfig, _containers: dict[str, Container]
    ) -> None:
        """Generate execution scripts for each service in each container.

        Creates shell scripts in per-container directories for each service
        with all necessary information to run that service and its microservices.

        Args:
            config: Simulation configuration.
            containers: Dictionary of container objects.
        """
        if self.output_manager is None:
            return

        for container_name, container_config in config.containers.items():
            for service_name in container_config.services:
                if service_name not in config.services:
                    continue

                service_config = config.services[service_name]
                script_content = self._generate_service_script_content(
                    service_name, service_config, config.microservices
                )
                self.output_manager.create_service_script(
                    container_name, service_name, script_content
                )

    @staticmethod
    def _generate_service_script_content(
        service_name: str, service_config: Any, microservices_config: dict[str, Any]
    ) -> str:
        """Generate Python web server script for a service.

        Creates a Flask/HTTP-based web server that:
        - Runs the service as a web server for inter-service communication
        - Executes microservices as tasks within the service
        - Handles dependencies and latency
        - Simulates errors based on configuration

        Args:
            service_name: Name of the service.
            service_config: Service configuration object.
            microservices_config: All microservices configurations.

        Returns:
            Python script content.
        """
        # Get microservices for this service
        microservices_list = []
        if hasattr(service_config, "microservices"):
            microservices_list = service_config.microservices

        # Build microservice definitions
        microservice_defs = {}

        def to_dict(obj: Any):
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if isinstance(obj, dict):
                return {k: to_dict(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [to_dict(v) for v in obj]
            return obj

        for ms_name in microservices_list:
            if ms_name in microservices_config:
                ms_cfg = microservices_config[ms_name]
                # Convert dependencies to dict if they are Pydantic models
                deps = getattr(ms_cfg, "dependencies", {})
                deps = to_dict(deps)

                microservice_defs[ms_name] = {
                    "error_rate": float(getattr(ms_cfg, "error_rate", 0.0)),
                    "latency": int(getattr(ms_cfg, "latency", 0)),
                    "work_difficulty": float(getattr(ms_cfg, "work_difficulty", 0.1)),
                    "dependencies": deps,
                }

        dependencies = to_dict(getattr(service_config, "dependencies", []))

        # Pre-compute JSON strings to avoid formatting issues in f-string
        deps_json = json.dumps(dependencies)
        microservices_json = json.dumps(microservice_defs, indent=6)

        script = f'''"""Web service runner for {service_name}.

Auto-generated service that:
- Runs as a web server for inter-service communication
- Executes microservices as tasks
- Handles dependencies and failures
"""

import json
import logging
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

logger = logging.getLogger(__name__)


class ServiceConfig:
    """Configuration for {service_name} service."""
    
    SERVICE_NAME = "{service_name}"
    PORT = 8000
    HOST = "0.0.0.0"
    
    DEPENDENCIES = {deps_json}
    
    MICROSERVICES = {microservices_json}


class MicroserviceExecutor:
    """Executes microservices with simulated latency and errors."""
    
    def __init__(self):
        self.call_count = {{}}
        self.error_count = {{}}
    
    def execute_microservice(self, microservice_name: str) -> dict:
        """Execute a microservice task.
        
        Args:
            microservice_name: Name of the microservice to execute.
        
        Returns:
            Result dictionary with execution details.
        """
        if microservice_name not in ServiceConfig.MICROSERVICES:
            return {{
                "status": "error",
                "message": f"Microservice {{microservice_name}} not found"
            }}
        
        ms_config = ServiceConfig.MICROSERVICES[microservice_name]
        
        # Track calls
        self.call_count[microservice_name] = self.call_count.get(microservice_name, 0) + 1
        
        # Simulate latency
        latency_ms = ms_config.get("latency", 0)
        if latency_ms > 0:
            time.sleep(latency_ms / 1000.0)
        
        # Simulate errors
        error_rate = ms_config.get("error_rate", 0.0)
        if random.random() < error_rate:
            self.error_count[microservice_name] = self.error_count.get(microservice_name, 0) + 1
            return {{
                "status": "error",
                "microservice": microservice_name,
                "message": "Simulated error"
            }}
        
        return {{
            "status": "success",
            "microservice": microservice_name,
            "latency_ms": latency_ms,
            "call_count": self.call_count[microservice_name]
        }}
    
    def get_stats(self) -> dict:
        """Get execution statistics."""
        return {{
            "calls": self.call_count,
            "errors": self.error_count
        }}


class ServiceRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for service API."""
    
    microservice_executor = MicroserviceExecutor()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {{
                "service": ServiceConfig.SERVICE_NAME,
                "status": "healthy"
            }}
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/stats":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {{
                "service": ServiceConfig.SERVICE_NAME,
                "stats": self.microservice_executor.get_stats()
            }}
            self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to execute microservices."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            request = json.loads(body)
            
            microservice_name = request.get("microservice")
            
            if not microservice_name:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {{
                    "error": "Missing microservice name"
                }}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Execute the microservice
            result = self.microservice_executor.execute_microservice(microservice_name)
            
            # Send response
            status_code = 200 if result.get("status") == "success" else 500
            self.send_response(status_code)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {{
                "error": str(e)
            }}
            self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


def main():
    """Start the service web server."""
    server = HTTPServer(
        (ServiceConfig.HOST, ServiceConfig.PORT),
        ServiceRequestHandler
    )
    
    logger.info(
        "Service %s starting on port %s...",
        ServiceConfig.SERVICE_NAME,
        ServiceConfig.PORT,
    )
    logger.info("Microservices: %s", list(ServiceConfig.MICROSERVICES.keys()))
    logger.info("Dependencies: %s", ServiceConfig.DEPENDENCIES)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Service %s shutting down...", ServiceConfig.SERVICE_NAME)
        server.shutdown()


if __name__ == "__main__":
    main()
'''
        return script

    @staticmethod
    def _run_single_container(
        container: Container,
        microservices: dict[str, Microservice],
        services: dict[str, Service],
        service_owners: dict[str, str],
        request_count: int,
        root_service_name: str,
    ) -> dict[str, Any]:
        """Execute a single container and collect metrics.

        Args:
            container: Container to execute.
            microservices: Available microservices dictionary.
            request_count: Number of requests per service.

        Returns:
            Container execution results.
        """
        context = ExecutionContext(
            microservices=microservices,
            services=services,
            service_owners=service_owners,
        )
        started_at = time.perf_counter()
        if root_service_name not in container.services:
            raise RuntimeError(
                f"Root service '{root_service_name}' not found in container '{container.name}'"
            )
        result = container.services[root_service_name].execute(
            context=context,
            request_count=request_count,
        )
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        return {
            "container": container.name,
            "elapsedMs": round(elapsed_ms, 3),
            "services": [
                {
                    "name": result.service_name,
                    "calls": result.calls,
                    "success": result.success,
                    "failures": result.failures,
                    "successRate": round(result.success_rate, 4),
                }
            ],
            "microservices": {
                name: {
                    "calls": metric.calls,
                    "failures": metric.failures,
                    "dependencyCalls": metric.dependency_calls,
                    "avgLatencyMs": (
                        round(metric.total_ms / metric.calls, 4) if metric.calls else 0.0
                    ),
                }
                for name, metric in sorted(context.metrics.items())
            },
        }
