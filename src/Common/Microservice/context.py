"""Execution context for microservice simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.Common.Microservice.metrics import ExecutionMetrics
from src.Common.Utils.logger import get_logger

if TYPE_CHECKING:
    from src.Common.Microservice.microservice import Microservice
    from src.Common.Service.service import Service

logger = get_logger(__name__)


@dataclass
class ExecutionContext:
    """Execution context shared across microservice invocations.

    Maintains the global state of microservice availability and metrics
    tracking throughout the simulation execution.

    Attributes:
        microservices: Dictionary of available microservices indexed by name.
        service_owners: Microservice to service ownership mapping.
        metrics: Metrics for each microservice indexed by name.
    """

    microservices: dict[str, "Microservice"]
    services: dict[str, "Service"] = field(default_factory=dict)
    service_owners: dict[str, str] = field(default_factory=dict)
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
            logger.debug("Created metrics for microservice: %s", name)
        return self.metrics[name]

    def service_for_microservice(self, microservice_name: str) -> str:
        """Return the service that owns a given microservice."""
        try:
            return self.service_owners[microservice_name]
        except KeyError as exc:
            raise RuntimeError(
                f"Microservice '{microservice_name}' is not mapped to a service"
            ) from exc
