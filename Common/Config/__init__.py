from __future__ import annotations
import json
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pathlib import Path
from typing import Annotated


ConfigKey = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_]+$")]


class DependencyConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    call_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        alias="callRate",
        description="Call rate as a decimal between 0 and 1",
    )
    stop_on_error: bool = Field(
        ...,
        alias="stopOnError",
        description="Whether to stop on error",
    )


class MicroserviceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dependencies: dict[ConfigKey, DependencyConfig] = Field(
        ...,
        description="Dependencies of this microservice",
    )
    error_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        alias="errorRate",
        description="Error rate as a decimal between 0 and 1",
    )
    work_difficulty: float = Field(
        ...,
        ge=0.0,
        alias="workDifficulty",
        description="Work difficulty level",
    )
    delay_ms: int = Field(
        default=0,
        ge=0,
        alias="delay",
        description="Delay in milliseconds",
    )


class ServiceMicroserviceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    can_restart: bool = Field(
        ...,
        alias="canRestart",
        description="Whether the microservice can restart",
    )


class ServiceConfig(BaseModel):
    microservices: dict[ConfigKey, ServiceMicroserviceConfig] = Field(
        ..., description="Microservices in this service"
    )


class ContainerServiceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    can_restart: bool = Field(
        ...,
        alias="canRestart",
        description="Whether the service can restart",
    )


class ContainerConfig(BaseModel):
    services: dict[ConfigKey, ContainerServiceConfig] = Field(
        ...,
        description="Services in this container",
    )


class SimulationConfig(BaseModel):
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
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        schema_path = output_path / "schema.json"
        with schema_path.open("w", encoding="utf-8") as f:
            json.dump(cls.model_json_schema(), f, indent=4)

        return schema_path


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
    from Common.Utils.error import print_error

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
