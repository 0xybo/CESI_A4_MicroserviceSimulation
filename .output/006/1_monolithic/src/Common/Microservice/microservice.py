"""Microservice execution unit."""

from __future__ import annotations

import random
import time

from src.Config import MicroserviceConfig
from src.Common.Microservice.context import ExecutionContext
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


class Microservice:
    """Simulates a single microservice unit.

    Executes work, simulates failures, and invokes dependencies based on
    the configuration provided.
    """

    def __init__(self, name: str, config: MicroserviceConfig) -> None:
        """Initialize a microservice.

        Args:
            name: The microservice name.
            config: Configuration for this microservice.
        """
        self.name = name
        self.config = config
        logger.debug(
            "Microservice '%s' initialized with work_difficulty=%s, error_rate=%s, delay_ms=%s",
            name,
            config.work_difficulty,
            config.error_rate,
            config.delay_ms,
        )

    def execute(self, context: ExecutionContext) -> bool:
        """Execute the microservice with its dependencies.

        Performs work simulation, applies error rates, handles delays,
        and recursively executes dependencies based on configuration.

        Args:
            context: The execution context with available microservices.

        Returns:
            True if execution succeeded, False if it failed.
        """
        metric = context.metric_for(self.name)
        metric.calls += 1
        started_at = time.perf_counter()
        logger.debug("Executing microservice '%s' (call #%s)", self.name, metric.calls)
        owning_service_name = context.service_for_microservice(self.name)

        try:
            if self.config.delay_ms > 0:
                logger.debug(
                    "Microservice '%s' applying delay: %sms", self.name, self.config.delay_ms
                )
                time.sleep(self.config.delay_ms / 1000)

            self._simulate_work()

            if random.random() < self.config.error_rate:
                logger.warning(
                    "Microservice '%s' simulated failure (error_rate=%s)",
                    self.name,
                    self.config.error_rate,
                )
                metric.failures += 1
                return False

            for dependency_name, dependency in self.config.dependencies.items():
                calls_to_run = max(0, int(round(dependency.call_rate)))
                for _ in range(calls_to_run):
                    metric.dependency_calls += 1
                    logger.debug(
                        "Microservice '%s' calling dependency '%s'", self.name, dependency_name
                    )
                    dependency_service_name = context.service_for_microservice(dependency_name)
                    if dependency_service_name == owning_service_name:
                        dependency_succeeded = context.microservices[dependency_name].execute(
                            context
                        )
                    else:
                        if dependency_service_name not in context.services:
                            raise RuntimeError(
                                f"Service '{dependency_service_name}' for microservice '{dependency_name}'"
                                " not found in context"
                            )
                        dependency_result = context.services[dependency_service_name].execute(
                            context,
                            1,
                            microservice_name=dependency_name,
                        )
                        dependency_succeeded = dependency_result.failures == 0

                    if not dependency_succeeded and dependency.stop_on_error:
                        logger.warning(
                            "Microservice '%s' dependency '%s' failed with stop_on_error=True",
                            self.name,
                            dependency_name,
                        )
                        metric.failures += 1
                        return False

            logger.debug("Microservice '%s' executed successfully", self.name)
            return True
        finally:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            metric.total_ms += elapsed_ms
            logger.debug("Microservice '%s' execution completed in %.2fms", self.name, elapsed_ms)

    def _simulate_work(self) -> None:
        """Simulate CPU-bound work for this microservice.

        Performs deterministic work to represent the microservice's business logic
        without creating non-deterministic system dependencies.
        """
        # Keep CPU work deterministic enough for comparisons across runs.
        iterations = max(0, int(self.config.work_difficulty * 20_000))
        value = 0
        for index in range(iterations):
            value += index % 13
        if value < 0:
            raise RuntimeError("Unreachable guard")
