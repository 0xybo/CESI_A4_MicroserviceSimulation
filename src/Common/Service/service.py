"""Service execution unit."""

from __future__ import annotations

from src.Config import ServiceConfig
from src.Common.Microservice.context import ExecutionContext
from src.Common.Service.result import ServiceRunResult


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
        success = 0
        failures = 0

        ordered_microservices = list(self.config.microservices.keys())

        for _ in range(request_count):
            request_ok = True
            for microservice_name in ordered_microservices:
                if not context.microservices[microservice_name].execute(context):
                    request_ok = False
                    break

            if request_ok:
                success += 1
            else:
                failures += 1

        return ServiceRunResult(
            service_name=self.name,
            calls=request_count,
            success=success,
            failures=failures,
        )
