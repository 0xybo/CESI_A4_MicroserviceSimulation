"""Docker platform module entry point and CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.Docker.platform import DockerPlatform


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
                print(json_output)
            platform.cleanup()
            return 0

        else:
            print("Error: No command specified. Use 'build' or 'run'.")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    exit(main(args))
