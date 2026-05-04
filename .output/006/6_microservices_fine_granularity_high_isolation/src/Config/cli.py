"""Command-line interface for configuration management."""

import json
from argparse import ArgumentParser, Namespace

from src.Common.Utils.logger import get_logger
from . import load_simulation_config
from .simulation_config import SimulationConfig
from .build import build

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
        "Configuration command received with args: input=%s, output=%s",
        getattr(args, "input", None),
        getattr(args, "output", None),
    )
    try:
        if args.input:
            logger.info("Loading configuration from file: %s", args.input)
            config = load_simulation_config(args.input)
            logger.info(
                "Configuration validated: containers=%d, services=%d, microservices=%d",
                len(config.containers),
                len(config.services),
                len(config.microservices),
            )
            logger.info("Configuration JSON:\n%s", config.model_dump_json(indent=4, by_alias=True))
        elif args.output:
            logger.info("Generating schema to output directory: %s", args.output)
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
        logger.error("Error in configuration processing: %s", e, exc_info=True)
        logger.error("Error generating schema: %s", e)
