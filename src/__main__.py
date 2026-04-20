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
from argparse import ArgumentParser

from src.Config.cli import config_parser, main as config_main
from src.Common.Utils.error import print_error
from src.Python.build import build as build_python
from src.Docker.build import build_docker_compose_file as build_docker


def main():
    """Main entry point for CLI.

    Parses arguments and dispatches to appropriate command handlers.
    """
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
        description=(
            "Build the simulation environment, supporting python and docker "
            "environments. If no environment is specified, builds both."
        ),
    )
    build_parser.add_argument(
        "environment",
        nargs="?",
        choices=["python", "docker"],
        help="The environment to build (default: both)",
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

    args = parser.parse_args()

    try:
        match args.command:
            case "config":
                config_main(args)
            case "build":
                env = args.environment
                if env == "python":
                    print("Building Python environment...")
                    build_python(args.config, args.output)
                    print("✓ Python environment built successfully")
                elif env == "docker":
                    print("Building Docker environment...")
                    build_docker(args.config, args.output)
                    print("✓ Docker environment built successfully")
                else:
                    # Build both when no environment specified
                    print("Building Python environment...")
                    build_python(args.config, args.output)
                    print("✓ Python environment built successfully")
                    print("Building Docker environment...")
                    build_docker(args.config, args.output)
                    print("✓ Docker environment built successfully")
            case _:
                print_error("Unknown command. Use --help for usage information.")
    except (
        KeyError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        RuntimeError,
    ) as e:  # pylint: disable=broad-except
        print_error(f"Error: {e}")


if __name__ == "__main__":
    main()
