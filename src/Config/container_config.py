"""
Container configuration models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .utils import ConfigKey
from .container_service_config import ContainerServiceConfig


class ContainerConfig(BaseModel):  # pylint: disable=missing-class-docstring
    services: dict[ConfigKey, ContainerServiceConfig] = Field(
        ...,
        description="Services in this container",
    )
