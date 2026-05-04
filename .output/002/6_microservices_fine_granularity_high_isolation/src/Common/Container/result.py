"""Container execution results."""

from __future__ import annotations

from dataclasses import dataclass

from src.Common.Service.result import ServiceRunResult


@dataclass
class ContainerRunResult:
    """Results from executing a container.

    Attributes:
        container_name: Name of the container.
        service_results: List of results from services executed in the container.
    """

    container_name: str
    service_results: list[ServiceRunResult]
