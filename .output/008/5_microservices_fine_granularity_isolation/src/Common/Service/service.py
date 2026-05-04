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
        logger.debug(
            "Service '%s' initialized with %d microservices and %d dependencies",
            name,
            len(config.microservices),
            len(config.dependencies),
        )

    def execute(
        self,
        context: ExecutionContext,
        request_count: int,
        microservice_name: str | None = None,
    ) -> ServiceRunResult:
        """Execute the service with multiple requests.

        For each request, calls the configured entrypoint microservice by default,
        or a specific microservice when `microservice_name` is provided. That
        microservice can recursively call its dependencies.

        Args:
            context: The execution context with available microservices.
            request_count: Number of requests to process.

        Returns:
            A ServiceRunResult with aggregated metrics.
        """
        logger.info("Service '%s' starting execution with %d requests", self.name, request_count)
        success = 0
        failures = 0

        entrypoint_name = microservice_name or self.config.entrypoint
        if entrypoint_name is not None and entrypoint_name not in self.config.microservices:
            raise RuntimeError(
                f"Service '{self.name}' microservice '{entrypoint_name}'" " not found in context"
            )

        if entrypoint_name is not None:
            logger.debug("Service '%s' entrypoint: %s", self.name, entrypoint_name)

        for request_idx in range(request_count):
            logger.debug(
                "Service '%s' processing request #%d/%d",
                self.name,
                request_idx + 1,
                request_count,
            )
            request_ok = True

            if entrypoint_name is not None:
                # Call the target microservice, which recursively calls its dependencies.
                if not context.microservices[entrypoint_name].execute(context):
                    request_ok = False
                    logger.warning(
                        "Service '%s' request #%d failed at microservice '%s'",
                        self.name,
                        request_idx + 1,
                        entrypoint_name,
                    )

            if request_ok:
                success += 1
            else:
                failures += 1

        logger.info(
            "Service '%s' execution completed: %d successes, %d failures (rate: %d/%d)",
            self.name,
            success,
            failures,
            success,
            request_count,
        )
        return ServiceRunResult(
            service_name=self.name,
            calls=request_count,
            success=success,
            failures=failures,
        )
