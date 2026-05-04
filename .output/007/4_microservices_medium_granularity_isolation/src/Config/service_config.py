"""
Defines configuration models for microservices and services using Pydantic.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .dependency_config import DependencyConfig
from .utils import ConfigKey
from .service_microservice_config import ServiceMicroserviceConfig


class ServiceConfig(BaseModel):  # pylint: disable=missing-class-docstring
    model_config = ConfigDict(populate_by_name=True)

    entrypoint: ConfigKey | None = Field(
        default=None,
        description=(
            "Name of the microservice to call at the beginning of a request; if omitted,"
            " the service can act as a client that only calls dependent services"
        ),
    )
    dependencies: dict[ConfigKey, DependencyConfig] = Field(
        default_factory=dict,
        description="Services called by this service in order",
    )
    microservices: dict[ConfigKey, ServiceMicroserviceConfig] = Field(
        default_factory=dict,
        description="Microservices in this service",
    )
