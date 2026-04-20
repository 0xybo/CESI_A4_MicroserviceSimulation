"""Python thread-based simulation executor for microservice architectures.

This module implements the execution logic for simulating distributed microservices
using Python threading. It orchestrates microservices, services, and containers
to measure performance metrics (latency, throughput, error rates) across different
deployment configurations.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from pathlib import Path
from typing import Any

# Access ThreadPoolExecutor through module to avoid false linter positives
ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor
as_completed = concurrent.futures.as_completed

from Common.Config import SimulationConfig, load_simulation_config
from Common.Container.__main__ import Container
from Common.Microservice.__main__ import ExecutionContext, Microservice
from Common.Service.__main__ import Service


def build_runtime(
    config: SimulationConfig,
) -> tuple[dict[str, Microservice], dict[str, Service], dict[str, Container]]:
    """Build runtime objects from simulation configuration.

    Creates Microservice, Service, and Container instances from the parsed
    configuration, establishing the runtime hierarchy for the simulation.

    Args:
        config: The parsed simulation configuration.

    Returns:
        A tuple of (microservices, services, containers) dictionaries indexed by name.
    """
    microservices = {
        name: Microservice(name, ms_config)
        for name, ms_config in config.microservices.items()
    }

    services = {
        name: Service(name, service_config)
        for name, service_config in config.services.items()
    }

    containers = {
        name: Container(name, container_config, services)
        for name, container_config in config.containers.items()
    }

    return microservices, services, containers


def run_single_container(
    container: Container, microservices: dict[str, Microservice], request_count: int
) -> dict[str, Any]:
    """Execute a single container and collect performance metrics.

    Runs the container with the specified number of requests and tracks execution
    time, service-level metrics, and microservice-level performance data.

    Args:
        container: The container to execute.
        microservices: Dictionary of available microservices for dependency resolution.
        request_count: Number of requests to send to each service.

    Returns:
        A dictionary containing container execution results and metrics.
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


def run_simulation(
    config_path: Path, request_count: int, workers: int
) -> dict[str, Any]:
    """Run the full microservice simulation with optional parallelization.

    Executes all containers defined in the configuration, with support for
    multi-threaded parallel execution when workers > 1.

    Args:
        config_path: Path to the simulation configuration JSON file.
        request_count: Number of requests per service.
        workers: Number of worker threads (1 = sequential, >1 = parallel).

    Returns:
        A dictionary containing aggregated results for all containers.
    """
    config = load_simulation_config(config_path)
    microservices, _services, containers = build_runtime(config)

    run_started_at = time.perf_counter()

    if workers <= 1:
        container_results = [
            run_single_container(container, microservices, request_count)
            for container in containers.values()
        ]
    else:
        container_results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    run_single_container, container, microservices, request_count
                )
                for container in containers.values()
            ]
            for future in as_completed(futures):
                container_results.append(future.result())

    total_elapsed_ms = (time.perf_counter() - run_started_at) * 1000

    return {
        "config": str(config_path),
        "requestCount": request_count,
        "workers": workers,
        "totalElapsedMs": round(total_elapsed_ms, 3),
        "containers": sorted(container_results, key=lambda item: item["container"]),
    }


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments.

    Returns:
        Parsed arguments namespace with config, requests, workers, and output.
    """
    parser = argparse.ArgumentParser(
        description="Run microservice architecture simulations."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config-test.json"),
        help="Path to the simulation config JSON file.",
    )
    parser.add_argument(
        "--requests", type=int, default=100, help="Number of requests per service."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker threads for container execution.",
    )
    parser.add_argument(
        "--output", type=Path, default=None, help="Optional path to write JSON results."
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for the simulation executor.

    Parses arguments, runs the simulation, and outputs results to stdout or file.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    args = parse_args()
    if args.requests <= 0:
        raise ValueError("--requests must be > 0")
    if args.workers <= 0:
        raise ValueError("--workers must be > 0")

    result = run_simulation(args.config, args.requests, args.workers)
    json_output = json.dumps(result, indent=2)

    if args.output is not None:
        args.output.write_text(json_output + "\n", encoding="utf-8")
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
