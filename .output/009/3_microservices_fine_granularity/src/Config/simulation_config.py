"""
Module for defining the configuration schema for microservice simulations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .utils import ConfigKey
from .service_config import ServiceConfig
from .container_config import ContainerConfig
from .microservice_config import MicroserviceConfig


class SimulationConfig(BaseModel):  # pylint: disable=missing-class-docstring
    entrypoint: ConfigKey | None = Field(
        default=None,
        description="Root service called by external requests",
    )
    request_count: int = Field(
        default=100,
        ge=1,
        alias="requestCount",
        description="Default number of requests to use when testing the generated architecture",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="logLevel",
        description="Default logging level for the shared application logger",
    )
    microservices: dict[ConfigKey, MicroserviceConfig] = Field(
        ...,
        description="All microservices in the simulation",
    )
    services: dict[ConfigKey, ServiceConfig] = Field(
        ...,
        description="All services in the simulation",
    )
    containers: dict[ConfigKey, ContainerConfig] = Field(
        ...,
        description="All containers in the simulation",
    )

    @classmethod
    def generate_schema_file(cls, output_dir: str | Path) -> Path:
        """Generate JSON schema file for the configuration.

        Args:
            output_dir: Directory where schema.json will be saved.

        Returns:
            Path to the generated schema file.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        schema_path = output_path / "schema.json"
        with schema_path.open("w", encoding="utf-8") as f:
            json.dump(cls.model_json_schema(), f, indent=4)

        return schema_path
