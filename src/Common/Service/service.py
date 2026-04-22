"""Service execution unit."""

from __future__ import annotations

from src.Config import ServiceConfig
from src.Common.Microservice.context import ExecutionContext
from src.Common.Service.result import ServiceRunResult
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


class Service:
    """Simulates a service as a composition of microservices.

    Coordinates the execution of its microservices in a defined order
    and aggregates results.
    """

    def __init__(self, name: str, config: ServiceConfig) -> None:
        """Initialize a service.

        Args:
            name: The service name.
            config: Configuration for this service.
        """
        self.name = name
        self.config = config
        logger.debug(f"Service '{name}' initialized with {len(config.microservices)} microservices")

    def execute(self, context: ExecutionContext, request_count: int) -> ServiceRunResult:
        """Execute the service with multiple requests.

        Processes the specified number of requests, executing microservices
        in order and aggregating success/failure metrics.

        Args:
            context: The execution context with available microservices.
            request_count: Number of requests to process.

        Returns:
            A ServiceRunResult with aggregated metrics.
        """
        logger.info(f"Service '{self.name}' starting execution with {request_count} requests")
        success = 0
        failures = 0

        ordered_microservices = list(self.config.microservices.keys())
        logger.debug(f"Service '{self.name}' microservices order: {ordered_microservices}")

        for request_idx in range(request_count):
            request_ok = True
            logger.debug(
                f"Service '{self.name}' processing request #{request_idx + 1}/{request_count}"
            )
            for microservice_name in ordered_microservices:
                if not context.microservices[microservice_name].execute(context):
                    logger.debug(
                        f"Service '{self.name}' request #{request_idx + 1} failed at microservice '{microservice_name}'"
                    )
                    request_ok = False
                    break

            if request_ok:
                success += 1
            else:
                failures += 1

        logger.info(
            f"Service '{self.name}' execution completed: {success} successes, {failures} failures (rate: {success}/{request_count})"
        )
        return ServiceRunResult(
            service_name=self.name,
            calls=request_count,
            success=success,
            failures=failures,
        )
