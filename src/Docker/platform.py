"""Docker-based platform implementation.

Provides a Platform implementation that executes simulations using Docker containers
via docker-compose, enabling containerized execution of microservice architectures.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from src.Common.Platform import Platform
from src.Common.Utils.logger import get_logger
from src.Config import SimulationConfig, load_simulation_config

logger = get_logger(__name__)


class DockerPlatform(Platform):
    """Platform implementation for Docker container-based execution.

    Executes microservice simulations using Docker Compose, with each container
    running a subset of services. Results are collected from mounted volumes.
    """

    def __init__(self) -> None:
        """Initialize Docker platform."""
        super().__init__()
        self.docker_compose_path: Path | None = None
        self.results_dir: Path | None = None

    def get_platform_name(self) -> str:
        """Get the platform name.

        Returns:
            "docker"
        """
        return "docker"

    def build(self, config_path: str | Path, output_dir: str | Path | None = None) -> None:
        """Build Docker execution environment.

        Validates Docker/docker-compose availability, generates docker-compose.yml,
        and creates timestamped test directory.

        Args:
            config_path: Path to simulation configuration.
            output_dir: Base directory for output (default: .output).

        Raises:
            RuntimeError: If environment validation or build fails.
        """
        if output_dir is None:
            output_dir = ".output"
        output_dir = Path(output_dir)
        config_path = Path(config_path)

        # Check config file exists
        if not config_path.exists():
            raise RuntimeError(f"Configuration file not found: {config_path}")

        # Check Docker availability
        try:
            subprocess.run(
                ["docker", "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.info("✓ Docker is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"Docker is not available or not installed: {e}") from e

        # Check docker-compose availability
        try:
            subprocess.run(
                ["docker-compose", "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.info("✓ docker-compose is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"docker-compose is not available or not installed: {e}") from e

        # Load and validate config
        try:
            config = load_simulation_config(config_path)
            logger.info("✓ Configuration valid: %s", config_path)
            logger.info("✓ Containers: %d", len(config.containers))
            logger.info("✓ Services: %d", len(config.services))
            logger.info("✓ Microservices: %d", len(config.microservices))
        except Exception as e:
            raise RuntimeError(f"Failed to validate configuration: {e}") from e

        # Initialize test output manager and create timestamped directory
        test_dir = self.initialize_output_manager(output_dir)

        # Save config to test directory
        self.output_manager.save_config(config)
        logger.info("✓ Test directory created: %s", test_dir)

        # Generate docker-compose.yml in test directory
        try:
            docker_compose_path = self._generate_docker_compose(config, test_dir)
            logger.info("✓ docker-compose.yml generated: %s", docker_compose_path)
            self.docker_compose_path = docker_compose_path
        except Exception as e:
            raise RuntimeError(f"Failed to generate docker-compose.yml: {e}") from e

    def execute(
        self,
        config_path: str,
        request_count: int,
        output_file: str | None = None,
        docker_compose_path: str | None = None,
        output_dir: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the simulation using Docker containers.

        Creates per-service scripts for each container and stores them
        in the test directory structure. Results and metrics are saved
        to the timestamped test output directory.

        Args:
            config_path: Path to simulation configuration.
            request_count: Number of requests per service.
            output_file: Optional path to write results.
            docker_compose_path: Path to docker-compose.yml to use.
            output_dir: Base output directory (default: .output).
            **kwargs: Additional arguments (unused).

        Returns:
            Execution results dictionary.

        Raises:
            RuntimeError: If execution fails.
        """
        if output_dir is None:
            output_dir = ".output"

        self.record_timing()

        try:
            config_path = Path(config_path)
            config = load_simulation_config(config_path)

            # Initialize test output if not already done
            if self.output_manager is None:
                self.initialize_output_manager(output_dir)
                self.output_manager.save_config(config)

            # Use provided or generate docker-compose.yml
            if docker_compose_path:
                compose_path = Path(docker_compose_path)
            elif self.docker_compose_path:
                compose_path = self.docker_compose_path
            else:
                raise RuntimeError("docker-compose.yml path not set; call build() first")

            if not compose_path.exists():
                raise RuntimeError(f"docker-compose.yml not found: {compose_path}")

            # Generate per-service scripts for each container
            self._generate_service_scripts(config, compose_path.parent)

            # Set up results directory in test directory
            test_dir = self.get_test_output_directory()
            results_dir = test_dir / "docker_results"
            results_dir.mkdir(parents=True, exist_ok=True)
            self.results_dir = results_dir

            # Run docker-compose up
            logger.info("Starting docker-compose from: %s", compose_path)
            run_started_at = time.perf_counter()

            subprocess.run(
                ["docker-compose", "-f", str(compose_path), "up", "--build"],
                check=True,
                cwd=str(compose_path.parent),
                timeout=300,  # 5 minute timeout
            )

            total_elapsed_ms = (time.perf_counter() - run_started_at) * 1000

            # Collect results from containers
            container_results = self._collect_results(results_dir, config)

            results = {
                "platform": self.get_platform_name(),
                "config": str(config_path),
                "requestCount": request_count,
                "totalElapsedMs": round(total_elapsed_ms, 3),
                "containers": container_results,
            }

            # Save results to test directory
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
                default_output = output_path_dir / "docker_simulation_results.json"
                default_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                logger.info("Results saved to: %s", default_output)

            self.complete_timing()
            return results

        except Exception as e:
            self.complete_timing()
            raise RuntimeError(f"Docker execution failed: {e}") from e

    def cleanup(self) -> None:
        """Clean up Docker resources and temporary files."""
        if self.docker_compose_path and self.docker_compose_path.exists():
            try:
                subprocess.run(
                    ["docker-compose", "-f", str(self.docker_compose_path), "down"],
                    check=False,
                    cwd=str(self.docker_compose_path.parent),
                    timeout=30,
                )
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Ignore cleanup errors

    def _generate_service_scripts(self, config: SimulationConfig, test_dir: Path) -> None:
        """Generate execution scripts for each service in each container.

        Creates shell scripts in per-container directories within the test directory
        for each service with all necessary information to run that service and its microservices.

        Args:
            config: Simulation configuration.
            test_dir: Test output directory where container folders are created.
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
        """Generate Python web server script for a Docker service.

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

        # Build microservice definitions
        microservice_defs = {}
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

        dependencies = getattr(service_config, "dependencies", [])

        # Pre-compute JSON strings to avoid formatting issues in f-string
        deps_json = json.dumps(dependencies)
        microservices_json = json.dumps(microservice_defs, indent=6)

        script = f'''"""Web service runner for {service_name} (Docker).

Auto-generated service that:
- Runs as a web server for inter-service communication
- Executes microservices as tasks
- Handles dependencies and failures
- Designed for Docker containerized deployment
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
    def _generate_docker_compose(config: SimulationConfig, output_dir: Path) -> Path:
        """Generate docker-compose.yml from configuration.

        Creates a docker-compose file with:
        - One service per container
        - Each service runs a simulation executor with its container's services
        - Shared results volume for collecting output
        - Network for inter-service communication

        Args:
            config: Simulation configuration.
            output_dir: Directory to write docker-compose.yml.

        Returns:
            Path to generated docker-compose.yml.
        """
        docker_compose = {
            "version": "3.9",
            "services": {},
            "volumes": {"results": {"driver": "local"}},
            "networks": {"simulation": {"driver": "bridge"}},
        }

        # Create a service for each container
        for container_name, container_config in config.containers.items():
            service_names = list(container_config.services.keys())

            # Service runs the Python simulation executor with its services
            docker_compose["services"][container_name] = {
                "build": {
                    "context": ".",
                    "dockerfile": "Dockerfile.executor",
                },
                "environment": {
                    "CONTAINER_NAME": container_name,
                    "SERVICES": ",".join(service_names),
                    "REQUEST_COUNT": "100",
                },
                "volumes": [
                    "results:/results",
                    "./config-test.json:/config.json:ro",
                ],
                "networks": ["simulation"],
                "depends_on": [],
            }

        compose_path = output_dir / "docker-compose.yml"
        with compose_path.open("w", encoding="utf-8") as f:
            json.dump(docker_compose, f, indent=2)

        return compose_path

    @staticmethod
    def _collect_results(results_dir: Path, config: SimulationConfig) -> list[dict[str, Any]]:
        """Collect execution results from containers.

        Reads JSON result files written by each container to the shared results volume.

        Args:
            results_dir: Directory containing result files.
            config: Configuration (for reference).

        Returns:
            List of container result dictionaries.
        """
        container_results = []

        for container_name in config.containers.keys():
            result_file = results_dir / f"{container_name}_result.json"
            if result_file.exists():
                try:
                    with result_file.open("r", encoding="utf-8") as f:
                        result = json.load(f)
                    container_results.append(result)
                except Exception:  # pylint: disable=broad-exception-caught
                    # Skip if result file is invalid
                    pass

        return sorted(container_results, key=lambda item: item.get("container", ""))
