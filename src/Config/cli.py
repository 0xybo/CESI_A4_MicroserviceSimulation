"""Command-line interface for configuration management."""

import json
from argparse import ArgumentParser, Namespace

from .simulation_config import SimulationConfig
from .build import build
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)

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
    logger.debug(
        f"Configuration command received with args: input={getattr(args, 'input', None)}, output={getattr(args, 'output', None)}"
    )
    try:
        if args.input:
            logger.info(f"Loading configuration from file: {args.input}")
            with open(
                args.input, "r", encoding="utf-8"
            ) as f:  # pylint: disable=consider-using-with
                config_data = json.load(f)
            logger.debug(f"Configuration file parsed successfully")
            config = SimulationConfig(**config_data)
            logger.info(
                f"Configuration validated: containers={len(config.containers)}, services={len(config.services)}, microservices={len(config.microservices)}"
            )
            print(config.model_dump_json(indent=4))
        elif args.output:
            logger.info(f"Generating schema to output directory: {args.output}")
            build(args.output)
        else:
            # If only --output not specified, default to .output folder
            logger.info("Generating schema to default output directory: .output")
            build(".output")
    except (
        json.JSONDecodeError,
        FileNotFoundError,
        ValueError,
    ) as e:  # pylint: disable=broad-except
        logger.error(f"Error in configuration processing: {e}", exc_info=True)
        print(f"Error generating schema: {e}")
