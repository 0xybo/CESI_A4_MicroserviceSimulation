"""Microservice execution unit."""

from __future__ import annotations

import random
import time

from src.Config import MicroserviceConfig
from src.Common.Microservice.context import ExecutionContext


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

        try:
            if self.config.delay_ms > 0:
                time.sleep(self.config.delay_ms / 1000)

            self._simulate_work()

            if random.random() < self.config.error_rate:
                metric.failures += 1
                return False

            for dependency_name, dependency in self.config.dependencies.items():
                calls_to_run = max(0, int(round(dependency.call_rate)))
                for _ in range(calls_to_run):
                    metric.dependency_calls += 1
                    dependency_result = context.microservices[dependency_name].execute(context)
                    if not dependency_result and dependency.stop_on_error:
                        metric.failures += 1
                        return False

            return True
        finally:
            metric.total_ms += (time.perf_counter() - started_at) * 1000

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
