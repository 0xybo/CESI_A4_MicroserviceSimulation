"""Service execution results."""

from __future__ import annotations

from dataclasses import dataclass


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
