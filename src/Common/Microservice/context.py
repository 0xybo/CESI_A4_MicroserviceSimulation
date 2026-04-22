"""Execution context for microservice simulation."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.Common.Microservice.metrics import ExecutionMetrics
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionContext:
    """Execution context shared across microservice invocations.

    Maintains the global state of microservice availability and metrics
    tracking throughout the simulation execution.

    Attributes:
        microservices: Dictionary of available microservices indexed by name.
        metrics: Metrics for each microservice indexed by name.
    """

    microservices: dict[str, "Microservice"]
    metrics: dict[str, ExecutionMetrics] = field(default_factory=dict)

    def metric_for(self, name: str) -> ExecutionMetrics:
        """Get or create metrics for a microservice.

        Args:
            name: The microservice name.

        Returns:
            The ExecutionMetrics instance for this microservice.
        """
        if name not in self.metrics:
            self.metrics[name] = ExecutionMetrics()
            logger.debug(f"Created metrics for microservice: {name}")
        return self.metrics[name]
