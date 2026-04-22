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
            f"Microservice '{name}' initialized with work_difficulty={config.work_difficulty}, error_rate={config.error_rate}, delay_ms={config.delay_ms}"
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
        logger.debug(f"Executing microservice '{self.name}' (call #{metric.calls})")

        try:
            if self.config.delay_ms > 0:
                logger.debug(f"Microservice '{self.name}' applying delay: {self.config.delay_ms}ms")
                time.sleep(self.config.delay_ms / 1000)

            self._simulate_work()

            if random.random() < self.config.error_rate:
                logger.warning(
                    f"Microservice '{self.name}' simulated failure (error_rate={self.config.error_rate})"
                )
                metric.failures += 1
                return False

            for dependency_name, dependency in self.config.dependencies.items():
                calls_to_run = max(0, int(round(dependency.call_rate)))
                for _ in range(calls_to_run):
                    metric.dependency_calls += 1
                    logger.debug(
                        f"Microservice '{self.name}' calling dependency '{dependency_name}'"
                    )
                    dependency_result = context.microservices[dependency_name].execute(context)
                    if not dependency_result and dependency.stop_on_error:
                        logger.warning(
                            f"Microservice '{self.name}' dependency '{dependency_name}' failed with stop_on_error=True"
                        )
                        metric.failures += 1
                        return False

            logger.debug(f"Microservice '{self.name}' executed successfully")
            return True
        finally:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            metric.total_ms += elapsed_ms
            logger.debug(f"Microservice '{self.name}' execution completed in {elapsed_ms:.2f}ms")

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
