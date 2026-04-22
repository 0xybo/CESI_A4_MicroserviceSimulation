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
from src.Config import SimulationConfig, load_simulation_config
from src.Common.Container.container import Container
from src.Common.Microservice.microservice import Microservice
from src.Common.Microservice.context import ExecutionContext
from src.Common.Service.service import Service
from src.Common.TestOutput import TestOutputManager

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
            print(f"✓ Configuration valid: {config_path}")
            print(f"✓ Containers: {len(config.containers)}")
            print(f"✓ Services: {len(config.services)}")
            print(f"✓ Microservices: {len(config.microservices)}")
        except Exception as e:
            raise RuntimeError(f"Failed to validate configuration: {e}") from e

        # Initialize test output manager
        test_dir = self.initialize_output_manager(output_dir)
        self.output_manager.save_config(config)
        print(f"✓ Test directory created: {test_dir}")

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
            f"Starting simulation execution: config={config_path}, requests={request_count}, workers={workers}"
        )
        if output_dir is None:
            output_dir = ".output"
            logger.debug("Using default output directory: .output")

        self.record_timing()

        try:
            config_path = Path(config_path)
            logger.debug(f"Loading simulation configuration from: {config_path}")
            config = load_simulation_config(config_path)
            logger.info(
                f"Configuration loaded: containers={len(config.containers)}, services={len(config.services)}, microservices={len(config.microservices)}"
            )

            # Initialize test output if not already done
            if self.output_manager is None:
                logger.debug("Initializing output manager")
                self.initialize_output_manager(output_dir)
                self.output_manager.save_config(config)

            logger.debug("Building runtime objects")
            microservices, _services, containers = self._build_runtime(config)
            logger.debug(
                f"Runtime built: microservices={len(microservices)}, containers={len(containers)}"
            )

            # Generate per-service scripts for each container
            logger.debug("Generating per-service scripts")
            self._generate_service_scripts(config, containers)

            run_started_at = time.perf_counter()
            logger.info(f"Executing {len(containers)} containers with {workers} worker(s)")

            if workers <= 1:
                logger.debug("Running containers sequentially")
                container_results = [
                    self._run_single_container(container, microservices, request_count)
                    for container in containers.values()
                ]
            else:
                logger.debug(f"Running containers in parallel with {workers} workers")
                container_results = []
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [
                        executor.submit(
                            self._run_single_container, container, microservices, request_count
                        )
                        for container in containers.values()
                    ]
                    for future in as_completed(futures):
                        container_results.append(future.result())

            total_elapsed_ms = (time.perf_counter() - run_started_at) * 1000
            logger.info(f"Simulation execution completed in {total_elapsed_ms:.2f}ms")

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
                logger.info(f"Results saved to: {results_path}")
                print(f"Results saved to: {results_path}")
            elif output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                logger.info(f"Results saved to: {output_path}")
                print(f"Results saved to: {output_path}")
            else:
                # Default to .output folder if no output file specified
                output_path_dir = Path(output_dir)
                output_path_dir.mkdir(parents=True, exist_ok=True)
                default_output = output_path_dir / "python_simulation_results.json"
                default_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                logger.info(f"Results saved to: {default_output}")
                print(f"Results saved to: {default_output}")

            self.complete_timing()
            return results

        except Exception as e:
            logger.error(f"Simulation execution failed: {e}", exc_info=True)
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

    def _generate_service_scripts(
        self, config: SimulationConfig, containers: dict[str, Container]
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
        for ms_name in microservices_list:
            if ms_name in microservices_config:
                ms_cfg = microservices_config[ms_name]
                # Convert dependencies to dict if they are Pydantic models
                deps = getattr(ms_cfg, "dependencies", {})

                # Recursively convert Pydantic models to dicts
                def to_dict(obj):
                    if hasattr(obj, "model_dump"):
                        return obj.model_dump()
                    elif isinstance(obj, dict):
                        return {k: to_dict(v) for k, v in obj.items()}
                    elif isinstance(obj, (list, tuple)):
                        return [to_dict(v) for v in obj]
                    else:
                        return obj

                deps = to_dict(deps)

                microservice_defs[ms_name] = {
                    "error_rate": float(getattr(ms_cfg, "error_rate", 0.0)),
                    "latency": int(getattr(ms_cfg, "latency", 0)),
                    "work_difficulty": float(getattr(ms_cfg, "work_difficulty", 0.1)),
                    "dependencies": deps,
                }

        dependencies = getattr(service_config, "dependencies", [])

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
import random
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


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
    
    print(f"Service {{ServiceConfig.SERVICE_NAME}} starting on port {{ServiceConfig.PORT}}...")
    print(f"Microservices: {{list(ServiceConfig.MICROSERVICES.keys())}}")
    print(f"Dependencies: {{ServiceConfig.DEPENDENCIES}}")
    print()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\nService {{ServiceConfig.SERVICE_NAME}} shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
'''
        return script

    @staticmethod
    def _run_single_container(
        container: Container, microservices: dict[str, Microservice], request_count: int
    ) -> dict[str, Any]:
        """Execute a single container and collect metrics.

        Args:
            container: Container to execute.
            microservices: Available microservices dictionary.
            request_count: Number of requests per service.

        Returns:
            Container execution results.
        """
        context = ExecutionContext(microservices=microservices)
        started_at = time.perf_counter()
        result = container.execute(context=context, request_count=request_count)
        elapsed_ms = (time.perf_counter() - started_at) * 1000

        return {
            "container": result.container_name,
            "elapsedMs": round(elapsed_ms, 3),
            "services": [
                {
                    "name": service_result.service_name,
                    "calls": service_result.calls,
                    "success": service_result.success,
                    "failures": service_result.failures,
                    "successRate": round(service_result.success_rate, 4),
                }
                for service_result in result.service_results
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
