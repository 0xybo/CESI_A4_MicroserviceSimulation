"""
Defines configuration models for microservices and services using Pydantic.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .utils import ConfigKey
from .service_microservice_config import ServiceMicroserviceConfig


class ServiceConfig(BaseModel):  # pylint: disable=missing-class-docstring
    microservices: dict[ConfigKey, ServiceMicroserviceConfig] = Field(
        ..., description="Microservices in this service"
    )
