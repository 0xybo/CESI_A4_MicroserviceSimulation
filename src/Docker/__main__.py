"""Docker platform module entry point and CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.Docker.build import stop_docker_compose_file
from src.Docker.build import test_docker_compose_file
from src.Docker.platform import DockerPlatform
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser for Docker platform CLI.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="Docker-based microservice simulation platform.",
        prog="python -m src.Docker",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # build command
    build_cmd = subparsers.add_parser("build", help="Build docker-compose environment")
    build_cmd.add_argument(
        "--config",
        type=Path,
        default=Path("config-test.json"),
        help="Path to simulation configuration file.",
    )
    build_cmd.add_argument(
        "--output",
        type=Path,
        default=Path("."),
        help="Output directory for docker-compose.yml.",
    )

    # run command
    run_cmd = subparsers.add_parser("run", help="Run simulation in Docker")
    run_cmd.add_argument(
        "--config",
        type=Path,
        default=Path("config-test.json"),
        help="Path to simulation configuration file.",
    )
    run_cmd.add_argument(
        "--compose",
        type=Path,
        required=True,
        help="Path to docker-compose.yml file.",
    )
    run_cmd.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Number of requests per service.",
    )
    run_cmd.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write JSON results.",
    )

    test_cmd = subparsers.add_parser(
        "test",
        help="Run requests against the Docker stack and measure performance",
        description=(
            "Executes the specified number of requests per service against a running Docker"
            " architecture, measuring request duration and per-container resource consumption."
        ),
    )
    test_cmd.add_argument(
        "--requests",
        type=str,
        default=None,
        help=(
            "Number of requests per service, or semicolon-separated list of values"
            " (e.g. '1;5;10'). If not specified, uses config value"
        ),
    )
    test_cmd.add_argument(
        "--output",
        type=Path,
        default=Path(".output"),
        help=(
            "Output directory where the generated folder is located (searches for most recent"
            " docker-compose.yml if --compose not specified)"
        ),
    )
    test_cmd.add_argument(
        "--compose",
        type=Path,
        default=None,
        help="Optional path to specific docker-compose.yml file to test against",
    )

    stop_cmd = subparsers.add_parser("stop", help="Stop and remove the Docker stack")
    stop_cmd.add_argument(
        "--compose",
        type=Path,
        default=None,
        help="Path to docker-compose.yml file.",
    )
    stop_cmd.add_argument(
        "--output",
        type=Path,
        default=Path(".output"),
        help="Output directory to search when compose is omitted.",
    )

    return parser


def main(args: argparse.Namespace) -> int:
    """Main entry point for Docker platform CLI.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    try:
        platform = DockerPlatform()

        if args.command == "build":
            platform.build(str(args.config), str(args.output))
            return 0

        elif args.command == "run":
            result = platform.execute(
                str(args.config),
                args.requests,
                output_file=str(args.output) if args.output else None,
                docker_compose_path=str(args.compose),
            )
            json_output = json.dumps(result, indent=2)
            if args.output:
                args.output.write_text(json_output + "\n", encoding="utf-8")
            else:
                logger.info("Simulation result:\n%s", json_output)
            platform.cleanup_runtime()
            return 0

        elif args.command == "test":
            from src.Config.utils import parse_requests_arg

            parsed = parse_requests_arg(args.requests)
            if isinstance(parsed, list):
                for rc in parsed:
                    result = test_docker_compose_file(
                        compose_path=str(args.compose) if args.compose else None,
                        output_dir=str(args.output),
                        request_count=rc,
                    )
                    summary = result.get("summary") if isinstance(result, dict) else {}
                    logger.info(
                        "Docker test completed (requests=%s): mean request duration %.3f ms, mean "
                        "resources %.3f%%",
                        rc,
                        summary.get("meanRequestDurationMs", 0) if isinstance(summary, dict) else 0,
                        (
                            summary.get("meanResourceUsagePercent", 0)
                            if isinstance(summary, dict)
                            else 0
                        ),
                    )
            else:
                result = test_docker_compose_file(
                    compose_path=str(args.compose) if args.compose else None,
                    output_dir=str(args.output),
                    request_count=parsed,
                )
                summary = result.get("summary") if isinstance(result, dict) else {}
                logger.info(
                    "Docker test completed: mean request duration %.3f ms, mean resources %.3f%%",
                    summary.get("meanRequestDurationMs", 0) if isinstance(summary, dict) else 0,
                    summary.get("meanResourceUsagePercent", 0) if isinstance(summary, dict) else 0,
                )
            return 0

        elif args.command == "stop":
            stop_docker_compose_file(
                compose_path=str(args.compose) if args.compose else None,
                output_dir=str(args.output),
            )
            return 0

        else:
            logger.error("No command specified. Use 'build', 'run', 'test', or 'stop'.")
            return 1

    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as e:
        logger.error("Error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    cli_parser = build_parser()
    parsed_args = cli_parser.parse_args()
    sys.exit(main(parsed_args))
