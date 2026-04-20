"""Python thread-based simulation executor for microservice architectures.

This module implements the execution logic for simulating distributed microservices
using Python threading. It orchestrates microservices, services, and containers
to measure performance metrics (latency, throughput, error rates) across different
deployment configurations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.Python.platform import PythonPlatform


# Legacy compatibility functions - delegate to PythonPlatform
def run_simulation(config_path: Path, request_count: int, workers: int) -> dict[str, Any]:
    """Run the full microservice simulation with optional parallelization.

    Executes all containers defined in the configuration, with support for
    multi-threaded parallel execution when workers > 1.

    This function maintains backward compatibility by delegating to PythonPlatform.

    Args:
        config_path: Path to the simulation configuration JSON file.
        request_count: Number of requests per service.
        workers: Number of worker threads (1 = sequential, >1 = parallel).

    Returns:
        A dictionary containing aggregated results for all containers.
    """
    platform = PythonPlatform()
    return platform.execute(str(config_path), request_count, workers=workers)


def parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments.

    Returns:
        Parsed arguments namespace with config, requests, workers, and output.
    """
    parser = argparse.ArgumentParser(description="Run microservice architecture simulations.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config-test.json"),
        help="Path to the simulation config JSON file.",
    )
    parser.add_argument("--requests", type=int, default=100, help="Number of requests per service.")
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker threads for container execution.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write JSON results (default: .output/python_simulation_results.json).",
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
