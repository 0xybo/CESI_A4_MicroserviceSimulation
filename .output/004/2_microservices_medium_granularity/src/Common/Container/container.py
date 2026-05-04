"""Container execution unit."""

from __future__ import annotations

from src.Config import ContainerConfig
from src.Common.Container.result import ContainerRunResult
from src.Common.Microservice.context import ExecutionContext
from src.Common.Service.service import Service
from src.Common.Service.result import ServiceRunResult
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


class Container:
    """Simulates a container as an aggregation of services.

    Manages service execution within container boundaries and aggregates results.
    """

    def __init__(self, name: str, config: ContainerConfig, services: dict[str, Service]) -> None:
        """Initialize a container.

        Args:
            name: The container name.
            config: Configuration for this container.
            services: Dictionary of services available to the container.
        """
        self.name = name
        self.config = config
        self.services = services
        logger.debug(
            "Container '%s' initialized with %d services: %s",
            name,
            len(services),
            list(services.keys()),
        )

    def execute(self, context: ExecutionContext, request_count: int) -> ContainerRunResult:
        """Execute all services in the container.

        Args:
            context: The execution context with available microservices.
            request_count: Number of requests per service.

        Returns:
            A ContainerRunResult with aggregated service results.
        """
        logger.info(
            "Container '%s' starting execution with %d services",
            self.name,
            len(self.config.services),
        )
        service_results: list[ServiceRunResult] = []

        for service_name in self.config.services:
            logger.debug("Container '%s' executing service '%s'", self.name, service_name)
            result = self.services[service_name].execute(context, request_count)
            service_results.append(result)
            logger.debug(
                "Container '%s' service '%s' completed: success=%d, failures=%d",
                self.name,
                service_name,
                result.success,
                result.failures,
            )

        logger.info(
            "Container '%s' execution completed with %d service results",
            self.name,
            len(service_results),
        )
        return ContainerRunResult(
            container_name=self.name,
            service_results=service_results,
        )
