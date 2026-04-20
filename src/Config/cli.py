"""Command-line interface for configuration management."""

import json
from argparse import ArgumentParser, Namespace

from .simulation_config import SimulationConfig
from .build import build

config_parser = ArgumentParser(
    "config",
    description="Print JSON schema or parsed config for SimulationConfig",
)
config_parser.add_argument(
    "--input",
    type=str,
    help="Path to a JSON file containing the simulation configuration",
    required=False,
)
config_parser.add_argument(
    "--output",
    type=str,
    help="Directory where the schema file will be saved",
    required=False,
)


def main(args: Namespace):
    """Process configuration command.

    Handles --input and --output options to validate and generate configurations.

    Args:
        args: Parsed command-line arguments.
    """
    try:
        if args.input:
            with open(
                args.input, "r", encoding="utf-8"
            ) as f:  # pylint: disable=consider-using-with
                config_data = json.load(f)
            config = SimulationConfig(**config_data)
            print(config.model_dump_json(indent=4))
        elif args.output:
            build(args.output)
        else:
            # If only --output not specified, default to .output folder
            build(".output")
    except (
        json.JSONDecodeError,
        FileNotFoundError,
        ValueError,
    ) as e:  # pylint: disable=broad-except
        print(f"Error generating schema: {e}")
