"""Service simulation entities and execution logic.

This module defines services as aggregations of microservices and handles
service-level execution and result collection.
"""

from __future__ import annotations

from dataclasses import dataclass

from Common.Config import ServiceConfig
from Common.Microservice.__main__ import ExecutionContext


@dataclass
class ServiceRunResult:
    """Results from executing a service.

    Attributes:
        service_name: Name of the service.
        calls: Total number of request calls processed.
        success: Number of successful requests.
        failures: Number of failed requests.
    """

    service_name: str
    calls: int
    success: int
    failures: int

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a fraction (0.0-1.0).

        Returns:
            The ratio of successful calls to total calls.
        """
        if self.calls == 0:
            return 0.0
        return self.success / self.calls


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

    def execute(
        self, context: ExecutionContext, request_count: int
    ) -> ServiceRunResult:
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
