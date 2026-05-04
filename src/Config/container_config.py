"""
Container configuration models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .utils import ConfigKey
from .container_service_config import ContainerServiceConfig


class ContainerConfig(BaseModel):  # pylint: disable=missing-class-docstring
    model_config = ConfigDict(populate_by_name=True)

    services: dict[ConfigKey, ContainerServiceConfig] = Field(
        ...,
        description="Services in this container",
    )
    cpu_limit: float = Field(
        default=0.5,
        gt=0,
        alias="cpuLimit",
        description="CPU limit to apply to the generated Docker Compose service",
    )
