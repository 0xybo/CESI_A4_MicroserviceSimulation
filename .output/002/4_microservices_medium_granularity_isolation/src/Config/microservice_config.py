"""
Defines the configuration schema for microservices in the simulation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .dependency_config import DependencyConfig
from .utils import ConfigKey


class MicroserviceConfig(BaseModel):  # pylint: disable=missing-class-docstring
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
