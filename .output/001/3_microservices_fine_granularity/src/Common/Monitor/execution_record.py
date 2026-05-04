"""Execution record data model for monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.Common.Monitor.metric import Metric


@dataclass
class ExecutionRecord:
    """Complete record of a single execution run.

    Attributes:
        execution_id: Unique identifier for this execution.
        platform_name: Name of the platform used.
        start_time: When execution started.
        end_time: When execution ended.
        config_path: Path to the configuration used.
        request_count: Number of requests processed.
        results: Full execution results (JSON-serializable dict).
        metrics: List of metrics recorded during execution.
    """

    execution_id: str
    platform_name: str
    start_time: datetime
    end_time: datetime
    config_path: str
    request_count: int
    results: dict[str, Any]
    metrics: list[Metric] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert execution record to dictionary for JSON serialization.

        Returns:
            Dictionary representation with all nested items serialized.
        """
        return {
            "execution_id": self.execution_id,
            "platform_name": self.platform_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "config_path": self.config_path,
            "request_count": self.request_count,
            "results": self.results,
            "metrics": [m.to_dict() for m in self.metrics],
        }
