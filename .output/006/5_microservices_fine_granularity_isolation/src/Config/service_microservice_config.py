"""
Module for microservice-specific configuration models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ServiceMicroserviceConfig(BaseModel):  # pylint: disable=missing-class-docstring
    model_config = ConfigDict(populate_by_name=True)

    can_restart: bool = Field(
        ...,
        alias="canRestart",
        description="Whether the microservice can restart",
    )
