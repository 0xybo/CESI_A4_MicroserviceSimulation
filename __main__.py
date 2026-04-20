from argparse import ArgumentParser
import json

from Common.Config.cli import config_parser, main as config_main
from Common.Utils.error import print_error

# Syntax : python -m . [command] [options]
#
# Commands :
#     - config [options] : Print JSON schema or parsed config for SimulationConfig
#       Options :
#           - --input [path] : Path to a JSON file containing the simulation configuration
#                              (default: config.json in current directory)
#           - --output [path] : Directory where the schema file will be saved (default: current directory)
#     - build [python,docker] : Build the simulation environment, this command supports python and docker environments.
#                               If no environment is specified, it will build both environments.
#
# Global options :
#    - --help : Show this help message and exit


def main():
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
        description="Build the simulation environment, this command supports python and docker environments. If no environment is specified, it will build both environments. ",
    )
    build_parser.add_argument(
        "environment",
        nargs="?",
        choices=["python", "docker"],
        help="The environment to build (default: both)",
    )

    args = parser.parse_args()

    try:
        match args.command:
            case "config":
                config_main(args)
            case "build":
                # Call the build main function with the specified environment
                pass
            case _:
                print_error("Unknown command. Use --help for usage information.")
    except (
        KeyError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as e:  # pylint: disable=broad-except
        print_error(f"Error: {e}")


if __name__ == "__main__":
    main()
