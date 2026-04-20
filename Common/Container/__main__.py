from __future__ import annotations

from dataclasses import dataclass

from Common.Config import ContainerConfig
from Common.Microservice.__main__ import ExecutionContext
from Common.Service.__main__ import Service, ServiceRunResult


@dataclass
class ContainerRunResult:
    container_name: str
    service_results: list[ServiceRunResult]


class Container:
    def __init__(
        self, name: str, config: ContainerConfig, services: dict[str, Service]
    ) -> None:
        self.name = name
        self.config = config
        self.services = services

    def execute(
        self, context: ExecutionContext, request_count: int
    ) -> ContainerRunResult:
        service_results: list[ServiceRunResult] = []

        for service_name in self.config.services:
            service_results.append(
                self.services[service_name].execute(context, request_count)
            )

        return ContainerRunResult(
            container_name=self.name,
            service_results=service_results,
        )
