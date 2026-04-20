"""Default in-memory Monitor implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.Common.Monitor.monitor import Monitor
from src.Common.Monitor.metric import Metric
from src.Common.Monitor.execution_record import ExecutionRecord


class DefaultMonitor(Monitor):
    """Simple in-memory implementation of Monitor.

    Stores all metrics and execution records in memory, providing
    JSON export functionality.
    """

    def __init__(self) -> None:
        """Initialize the default monitor."""
        self.metrics: list[Metric] = []
        self.executions: list[ExecutionRecord] = []

    def record_metric(self, metric: Metric) -> None:
        """Record a single metric.

        Args:
            metric: Metric to record.
        """
        self.metrics.append(metric)

    def record_execution(self, execution_record: ExecutionRecord) -> None:
        """Record a complete execution run.

        Args:
            execution_record: Full execution record to store.
        """
        self.executions.append(execution_record)

    def export_results(self, format: str = "json") -> str:
        """Export all recorded data.

        Args:
            format: Export format ("json" currently supported).

        Returns:
            JSON string representation of metrics and executions.

        Raises:
            ValueError: If format is not "json".
        """
        if format != "json":
            raise ValueError(f"Unsupported export format: {format}. Use 'json'.")

        data = {
            "metrics": [m.to_dict() for m in self.metrics],
            "executions": [e.to_dict() for e in self.executions],
        }
        return json.dumps(data, indent=2)

    def export_to_file(self, output_path: str | Path, format: str = "json") -> Path:
        """Export results to a file.

        Args:
            output_path: Path where results will be written.
            format: Export format ("json" currently supported).

        Returns:
            Path to written file.

        Raises:
            ValueError: If format is not supported.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        results = self.export_results(format)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(results)

        return output_path

    def clear(self) -> None:
        """Clear all recorded metrics and executions."""
        self.metrics = []
        self.executions = []

    def get_metric_count(self) -> int:
        """Get total number of recorded metrics.

        Returns:
            Number of metrics.
        """
        return len(self.metrics)

    def get_execution_count(self) -> int:
        """Get total number of recorded executions.

        Returns:
            Number of executions.
        """
        return len(self.executions)
