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

    def build(self, config_path: str, output_dir: str) -> None:
        """Build and validate the Python execution environment.

        Validates Python version, required dependencies (pydantic),
        and configuration file existence.

        Args:
            config_path: Path to simulation configuration.
            output_dir: Output directory (unused for Python platform).

        Raises:
            RuntimeError: If environment validation fails.
        """
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

    def execute(
        self,
        config_path: str,
        request_count: int,
        output_file: str | None = None,
        workers: int = 1,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the simulation using Python threads.

        Args:
            config_path: Path to simulation configuration.
            request_count: Number of requests per service.
            output_file: Optional path to write results.
            workers: Number of worker threads (default: 1).
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
            microservices, _services, containers = self._build_runtime(config)

            run_started_at = time.perf_counter()

            if workers <= 1:
                container_results = [
                    self._run_single_container(container, microservices, request_count)
                    for container in containers.values()
                ]
            else:
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

            results = {
                "platform": self.get_platform_name(),
                "config": str(config_path),
                "requestCount": request_count,
                "workers": workers,
                "totalElapsedMs": round(total_elapsed_ms, 3),
                "containers": sorted(container_results, key=lambda item: item["container"]),
            }

            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
            else:
                # Default to .output folder if no output file specified
                output_dir = Path(".output")
                output_dir.mkdir(parents=True, exist_ok=True)
                default_output = output_dir / "python_simulation_results.json"
                default_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
                print(f"Results saved to: {default_output}")

            self.complete_timing()
            return results

        except Exception as e:
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
