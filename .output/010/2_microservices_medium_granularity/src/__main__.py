"""Main entry point for the microservice simulation application.

Provides command-line interface for managing simulation configurations,
building environments, and running simulations.

Syntax:
    python -m . [command] [options]

Commands:
    - config [options] : Manage simulation configuration
      Options:
          - --input [path] : Path to JSON simulation configuration file
          - --output [path] : Directory to save schema file
    - build [python,docker] : Build simulation environment
      Options:
          - environment : python, docker, or both (default: both)

Global options:
    - --help : Show help message
"""

import json
import shutil
from argparse import ArgumentParser
from pathlib import Path

from src.Config.cli import config_parser, main as config_main
from src.Config.architecture_generator import generate_architecture_configs
from src.Common.Utils.logger import get_logger
from typing import Any

from src.Docker.build import build_docker_compose_file as build_docker
from src.Docker.build import stop_docker_compose_file as stop_docker
from src.Docker.build import test_all_docker_configs as test_all_docker
from src.Docker.build import test_docker_compose_file as test_docker
from src.Docker.build import run_docker_compose_file as run_docker
from src.Docker.result_plots import plot_docker_results

logger = get_logger(__name__)


def clean_output_directory(output_dir: str) -> None:
    """Remove all content from the output directory while keeping the directory."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    for child in output_path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    logger.info("Output directory cleaned: %s", output_path)


def main():
    """Main entry point for CLI.

    Parses arguments and dispatches to appropriate command handlers.
    """
    logger.debug("Initializing argument parser")
    parser = ArgumentParser(description="Microservice Simulation Configuration Tool")
    command_parser = parser.add_subparsers(dest="command", required=True)

    # Config
    command_parser.add_parser(
        name="config",
        parents=[config_parser],
        add_help=False,
    )

    # Build
    build_parser = command_parser.add_parser(
        name="build",
        description=("Build the Docker simulation environment."),
    )
    build_parser.add_argument(
        "environment",
        nargs="?",
        choices=["docker"],
        help="Optional compatibility argument; Docker is the only supported environment.",
    )
    build_parser.add_argument(
        "--config",
        type=str,
        default="config-test.json",
        help="Path to simulation configuration file.",
    )
    build_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Output directory for build artifacts (default: .output).",
    )

    # Run
    run_parser = command_parser.add_parser(
        name="run",
        description="Run the most recent generated Docker Compose environment.",
    )
    run_parser.add_argument(
        "--compose",
        type=str,
        default=None,
        help="Path to docker-compose.yml. Defaults to the newest one under --output.",
    )
    run_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Output directory to search when --compose is not provided.",
    )
    run_parser.add_argument(
        "--detach",
        action="store_true",
        help="Run containers in detached mode (default).",
    )

    # Test
    test_parser = command_parser.add_parser(
        name="test",
        description="Run requests against the latest generated Docker Compose environment.",
    )
    test_parser.add_argument(
        "--compose",
        type=str,
        default=None,
        help="Path to docker-compose.yml. Defaults to the newest one under --output.",
    )
    test_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Output directory to search when --compose is not provided.",
    )
    test_parser.add_argument(
        "--requests",
        type=str,
        default=None,
        help=(
            "Number of requests per service, or semicolon-separated list of values"
            " (e.g. '1;5;10'). Defaults to requestCount from config.json."
        ),
    )

    # Test all generated config families
    test_all_parser = command_parser.add_parser(
        name="test-all",
        description="Build and test every generated config.json under the output folder.",
    )
    test_all_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Root output directory containing generated architecture folders.",
    )
    test_all_parser.add_argument(
        "--requests",
        type=str,
        default=None,
        help=(
            "Number of requests per service for each config, or semicolon-separated"
            " list of values (e.g. '1;5;10'). Defaults to requestCount."
        ),
    )
    test_all_parser.add_argument(
        "--missing",
        action="store_true",
        help=(
            "Only run tests for configurations that are missing a result file"
            " for the given request count (skips if result_<N>.csv exists)."
        ),
    )

    # Plot results
    plot_parser = command_parser.add_parser(
        name="plot-results",
        description=(
            "Create line or bar plots from all generated result_<N>.csv files"
            " under the output folder."
        ),
    )
    plot_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Root output directory containing generated result CSV files.",
    )
    plot_parser.add_argument(
        "--plots-dir",
        type=str,
        default=None,
        help="Directory where plot images will be written (default: <output>/plots).",
    )
    plot_parser.add_argument(
        "--plot-type",
        choices=["line", "bar"],
        default="line",
        help="Plot style: line creates 6 architecture plots, bar creates 3 metric plots.",
    )

    # Stop
    stop_parser = command_parser.add_parser(
        name="stop",
        description="Stop and remove the generated Docker Compose environment.",
    )
    stop_parser.add_argument(
        "--compose",
        type=str,
        default=None,
        help="Path to docker-compose.yml. Defaults to the newest one under --output.",
    )
    stop_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Output directory to search when --compose is not provided.",
    )

    # Clean
    clean_parser = command_parser.add_parser(
        name="clean",
        description="Remove all content from the output directory.",
    )
    clean_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Output directory to clean (default: .output).",
    )

    # Generate architecture configuration families
    generate_parser = command_parser.add_parser(
        name="generate-configs",
        description="Generate 6 configuration files for each architecture by "
        "permuting dependencies.",
    )
    generate_parser.add_argument(
        "--count",
        type=int,
        required=True,
        help=(
            "Number of base dependency architectures to generate. "
            "Each architecture produces 6 level-specific config.json files."
        ),
    )
    generate_parser.add_argument(
        "--output",
        type=str,
        default=".output",
        help="Root output directory for generated configs (default: .output).",
    )
    generate_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducible architecture generation.",
    )

    args = parser.parse_args()
    logger.info("Command received: %s", args.command)

    try:
        match args.command:
            case "config":
                logger.info("Processing config command")
                config_main(args)
            case "build":
                logger.info("Building Docker environment...")
                build_docker(args.config, args.output)
                logger.info("Docker environment built successfully")
            case "run":
                logger.info("Running Docker environment...")
                run_docker(args.compose, args.output, detach=not args.detach)
                logger.info("Docker environment started successfully")
            case "test":
                logger.info("Testing Docker environment...")
                from src.Config.utils import parse_requests_arg

                parsed = parse_requests_arg(args.requests)
                if isinstance(parsed, list):
                    all_results: list[dict[str, Any]] = []
                    for rc in parsed:
                        logger.info("Running test with requestCount=%s", rc)
                        res = test_docker(args.compose, args.output, rc)
                        logger.info(
                            "Docker test completed (requests=%s): mean request duration %.3f "
                            "ms, mean resources %.3f%%",
                            rc,
                            res["summary"]["meanRequestDurationMs"],
                            res["summary"]["meanResourceUsagePercent"],
                        )
                        all_results.append(res)
                else:
                    results: dict[str, Any] = test_docker(args.compose, args.output, parsed)
                    logger.info(
                        "Docker test completed: mean request duration %.3f ms, mean"
                        " resources %.3f%%",
                        results["summary"]["meanRequestDurationMs"],
                        results["summary"]["meanResourceUsagePercent"],
                    )
            case "test-all":
                logger.info("Testing all generated Docker configs under %s...", args.output)
                from src.Config.utils import parse_requests_arg

                parsed = parse_requests_arg(args.requests)
                if isinstance(parsed, list):
                    all_results: list[dict[str, Any]] = []
                    for rc in parsed:
                        logger.info("Running test-all with requestCount=%s", rc)
                        res = test_all_docker(args.output, rc, missing=args.missing)
                        logger.info(
                            "Completed %d Docker config tests for requests=%s", len(res), rc
                        )
                        all_results.extend(res)
                else:
                    all_results = test_all_docker(args.output, parsed, missing=args.missing)
                    logger.info("Completed %d Docker config tests", len(all_results))
            case "plot-results":
                logger.info(
                    "Generating %s plots from result CSV files under %s...",
                    args.plot_type,
                    args.output,
                )
                generated_plots = plot_docker_results(args.output, args.plot_type, args.plots_dir)
                logger.info("Generated %d plot images", len(generated_plots))
            case "stop":
                logger.info("Stopping Docker environment...")
                stop_docker(args.compose, args.output)
                logger.info("Docker environment stopped successfully")
            case "clean":
                logger.info("Cleaning output directory: %s", args.output)
                clean_output_directory(args.output)
            case "generate-configs":
                logger.info("Generating %s architecture families in %s", args.count, args.output)
                written_files = generate_architecture_configs(args.count, args.output, args.seed)
                logger.info("Generated %d config files", len(written_files))
            case _:
                logger.error("Unknown command: %s", args.command)
                raise ValueError("Unknown command. Use --help for usage information.")
    except (
        KeyError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        RuntimeError,
    ) as e:  # pylint: disable=broad-except
        logger.error("Error: %s", e, exc_info=True)


if __name__ == "__main__":
    main()
