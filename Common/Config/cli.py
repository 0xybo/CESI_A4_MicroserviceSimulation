from argparse import ArgumentParser, Namespace
import json

from . import SimulationConfig
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
            schema_json = SimulationConfig.model_json_schema()
            print(json.dumps(schema_json, indent=4))
    except (
        json.JSONDecodeError,
        FileNotFoundError,
        ValueError,
    ) as e:  # pylint: disable=broad-except
        print(f"Error generating schema: {e}")
