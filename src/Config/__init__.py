"""
Configuration models and utilities for microservice simulations.

Provides Pydantic models for validating simulation configurations and
loading configurations from JSON files.
"""

from __future__ import annotations

import json
from pathlib import Path

from .simulation_config import SimulationConfig
from .container_config import ContainerConfig
from .service_config import ServiceConfig
from .microservice_config import MicroserviceConfig
from ..Common.Utils.error import print_error


def load_simulation_config(config_path: str | Path) -> SimulationConfig:
    """Load and validate simulation configuration from a JSON file.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        Validated SimulationConfig instance.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        json.JSONDecodeError: If JSON is invalid.
        ValidationError: If config doesn't match SimulationConfig schema.
    """
    # pylint: disable=import-outside-toplevel

    config_path = Path(config_path)

    if not config_path.exists():
        print_error(f"Configuration file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as f:
            config_data = json.load(f)
        return SimulationConfig(**config_data)
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in {config_path}: {e}")
    except (
        FileNotFoundError,
        OSError,
        ValueError,
    ) as e:  # pylint: disable=broad-except
        print_error(f"Failed to parse configuration: {e}")


__all__ = [
    "SimulationConfig",
    "ContainerConfig",
    "ServiceConfig",
    "MicroserviceConfig",
    "load_simulation_config",
]
