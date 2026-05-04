"""Execution metrics for microservice tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionMetrics:
    """Metrics for tracking microservice execution performance.

    Attributes:
        calls: Total number of calls to this microservice.
        failures: Number of calls that failed.
        total_ms: Total execution time in milliseconds.
        dependency_calls: Number of dependency calls made by this microservice.
    """

    calls: int = 0
    failures: int = 0
    total_ms: float = 0.0
    dependency_calls: int = 0
