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
from src.Config import SimulationConfig, load_simulation_config


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

    def build(self, config_path: str, output_dir: str) -> None:
        """Build Docker execution environment.

        Validates Docker/docker-compose availability and generates docker-compose.yml.

        Args:
            config_path: Path to simulation configuration.
            output_dir: Directory where docker-compose.yml will be written.

        Raises:
            RuntimeError: If environment validation or build fails.
        """
        config_path = Path(config_path)
        output_dir = Path(output_dir)

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
            print("✓ Docker is available")
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
            print("✓ docker-compose is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError(f"docker-compose is not available or not installed: {e}") from e

        # Load and validate config
        try:
            config = load_simulation_config(config_path)
            print(f"✓ Configuration valid: {config_path}")
            print(f"✓ Containers: {len(config.containers)}")
            print(f"✓ Services: {len(config.services)}")
            print(f"✓ Microservices: {len(config.microservices)}")
        except Exception as e:
            raise RuntimeError(f"Failed to validate configuration: {e}") from e

        # Generate docker-compose.yml
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            docker_compose_path = self._generate_docker_compose(config, output_dir)
            print(f"✓ docker-compose.yml generated: {docker_compose_path}")
            self.docker_compose_path = docker_compose_path
        except Exception as e:
            raise RuntimeError(f"Failed to generate docker-compose.yml: {e}") from e

    def execute(
        self,
        config_path: str,
        request_count: int,
        output_file: str | None = None,
        docker_compose_path: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the simulation using Docker containers.

        Args:
            config_path: Path to simulation configuration.
            request_count: Number of requests per service.
            output_file: Optional path to write results.
            docker_compose_path: Path to docker-compose.yml to use.
            **kwargs: Additional arguments (unused).

        Returns:
            Execution results dictionary.

        Raises:
            RuntimeError: If execution fails.
        """
        self.record_timing()

        try:
            config_path = Path(config_path)
            config = load_simulation_config(config_path)

            # Use provided or generate docker-compose.yml
            if docker_compose_path:
                compose_path = Path(docker_compose_path)
            elif self.docker_compose_path:
                compose_path = self.docker_compose_path
            else:
                raise RuntimeError("docker-compose.yml path not set; call build() first")

            if not compose_path.exists():
                raise RuntimeError(f"docker-compose.yml not found: {compose_path}")

            # Set up results directory in .output
            results_dir = Path(".output") / "docker_results"
            results_dir.mkdir(parents=True, exist_ok=True)
            self.results_dir = results_dir

            # Run docker-compose up
            print(f"Starting docker-compose from: {compose_path}")
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

            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
            else:
                # Default to .output folder if no output file specified
                output_dir = Path(".output")
                output_dir.mkdir(parents=True, exist_ok=True)
                default_output = output_dir / "docker_simulation_results.json"
                default_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                print(f"Results saved to: {default_output}")

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
            except Exception:
                pass  # Ignore cleanup errors

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
                except Exception:
                    # Skip if result file is invalid
                    pass

        return sorted(container_results, key=lambda item: item.get("container", ""))
