"""Abstract Monitor base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.Common.Monitor.metric import Metric
from src.Common.Monitor.execution_record import ExecutionRecord


class Monitor(ABC):
    """Abstract base class for execution monitoring.

    Monitors collect metrics and execution records from simulation runs,
    providing interface for recording and exporting data.
    """

    @abstractmethod
    def record_metric(self, metric: Metric) -> None:
        """Record a single metric.

        Args:
            metric: Metric to record.
        """

    @abstractmethod
    def record_execution(self, execution_record: ExecutionRecord) -> None:
        """Record a complete execution run.

        Args:
            execution_record: Full execution record to store.
        """

    @abstractmethod
    def export_results(self, format: str = "json") -> str:
        """Export all recorded data.

        Args:
            format: Export format ("json" currently supported).

        Returns:
            String representation of exported data.

        Raises:
            ValueError: If format is not supported.
        """

    def clear(self) -> None:
        """Clear all recorded metrics and executions.

        Default implementation does nothing; override to support clearing.
        """
