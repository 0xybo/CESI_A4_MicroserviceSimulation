"""
Dependency configuration model for microservice simulation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DependencyConfig(BaseModel):  # pylint: disable=missing-class-docstring
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
