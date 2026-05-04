"""Metric data model for monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Metric:
    """A single recorded metric during execution.

    Attributes:
        timestamp: When the metric was recorded.
        metric_name: Name of the metric (e.g., "container_elapsed_ms").
        value: Numeric or string value of the metric.
        tags: Dictionary of tags for filtering/grouping (platform, container, service, etc).
        platform_name: Name of the platform that recorded this metric.
    """

    timestamp: datetime
    metric_name: str
    value: float | int | str
    platform_name: str
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dictionary for JSON serialization.

        Returns:
            Dictionary representation with timestamp ISO formatted.
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "platform_name": self.platform_name,
            "tags": self.tags,
        }
