"""CSV monitor for request duration and aggregate container resources."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable

from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class MonitorSample:
    """Single collected monitoring sample."""

    timestamp: str
    event_type: str
    service_name: str | None = None
    request_index: int | None = None
    request_duration_ms: float | None = None
    resource_usage_percent: float | None = None
    mean_request_duration_ms: float | None = None
    mean_resource_usage_percent: float | None = None
    failed: bool | None = None

    def to_row(self) -> dict[str, Any]:
        """Convert the sample to a dictionary row for CSV export."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "service_name": self.service_name or "",
            "request_index": "" if self.request_index is None else self.request_index,
            "request_duration_ms": (
                "" if self.request_duration_ms is None else round(self.request_duration_ms, 3)
            ),
            "resource_usage_percent": (
                "" if self.resource_usage_percent is None else round(self.resource_usage_percent, 3)
            ),
            "mean_request_duration_ms": (
                ""
                if self.mean_request_duration_ms is None
                else round(self.mean_request_duration_ms, 3)
            ),
            "mean_resource_usage_percent": (
                ""
                if self.mean_resource_usage_percent is None
                else round(self.mean_resource_usage_percent, 3)
            ),
            "failed": "" if self.failed is None else int(bool(self.failed)),
        }


class DefaultMonitor:
    """Collect request durations and aggregate container resource usage."""

    csv_headers = [
        "timestamp",
        "event_type",
        "service_name",
        "request_index",
        "failed",
        "request_duration_ms",
        "resource_usage_percent",
        "mean_request_duration_ms",
        "mean_resource_usage_percent",
    ]

    def __init__(self, output_path: str | Path | None = None) -> None:
        self.output_path = Path(output_path) if output_path is not None else Path("result.csv")
        self._samples: list[MonitorSample] = []
        self._request_durations: list[float] = []
        self._resource_usages: list[float] = []
        self._latest_resource_usage: float = 0.0
        self._failed_requests: int = 0
        self._resource_sampler: Callable[[], float] | None = None
        self._resource_thread: Thread | None = None
        self._stop_event = Event()
        self._lock = Lock()

    def start_resource_monitor(
        self, resource_sampler: Callable[[], float], interval_seconds: float = 1.0
    ) -> None:
        """Start collecting aggregate resource usage samples in the background."""
        if self._resource_thread is not None and self._resource_thread.is_alive():
            return

        self._resource_sampler = resource_sampler
        self._stop_event.clear()

        def _run() -> None:
            while not self._stop_event.is_set():
                try:
                    usage = float(resource_sampler())
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning("Resource sampling failed: %s", exc)
                else:
                    self.record_resource_sample(usage)
                if self._stop_event.wait(interval_seconds):
                    break

        self._resource_thread = Thread(target=_run, name="monitor-resource-sampler", daemon=True)
        self._resource_thread.start()

    def stop_resource_monitor(self) -> None:
        """Stop background resource sampling."""
        self._stop_event.set()
        if self._resource_thread is not None:
            self._resource_thread.join(timeout=5)
        self._resource_thread = None

    def record_resource_sample(self, resource_usage_percent: float) -> None:
        """Store one aggregate resource sample."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        with self._lock:
            self._latest_resource_usage = resource_usage_percent
            self._resource_usages.append(resource_usage_percent)
            self._samples.append(
                MonitorSample(
                    timestamp=timestamp,
                    event_type="resource",
                    resource_usage_percent=resource_usage_percent,
                    mean_request_duration_ms=self.mean_request_duration_ms(),
                    mean_resource_usage_percent=self.mean_resource_usage_percent(),
                )
            )

    def record_request(
        self,
        service_name: str,
        request_index: int,
        request_duration_ms: float,
        resource_usage_percent: float | None = None,
        success: bool = True,
    ) -> None:
        """Store one request-duration measurement."""
        timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        if resource_usage_percent is None:
            resource_usage_percent = self._latest_resource_usage

        with self._lock:
            self._request_durations.append(request_duration_ms)
            if not success:
                self._failed_requests += 1
            self._samples.append(
                MonitorSample(
                    timestamp=timestamp,
                    event_type="request",
                    service_name=service_name,
                    request_index=request_index,
                    request_duration_ms=request_duration_ms,
                    resource_usage_percent=resource_usage_percent,
                    mean_request_duration_ms=self.mean_request_duration_ms(),
                    mean_resource_usage_percent=self.mean_resource_usage_percent(),
                    failed=not success,
                )
            )

    def mean_request_duration_ms(self) -> float:
        """Return the average request duration in milliseconds."""
        if not self._request_durations:
            return 0.0
        return sum(self._request_durations) / len(self._request_durations)

    def mean_resource_usage_percent(self) -> float:
        """Return the average aggregate resource usage percent."""
        if not self._resource_usages:
            return 0.0
        return sum(self._resource_usages) / len(self._resource_usages)

    def summary(self) -> dict[str, float | int]:
        """Return the current counts and means."""
        return {
            "requestCount": len(self._request_durations),
            "failedRequestCount": self._failed_requests,
            "resourceSampleCount": len(self._resource_usages),
            "meanRequestDurationMs": round(self.mean_request_duration_ms(), 3),
            "meanResourceUsagePercent": round(self.mean_resource_usage_percent(), 3),
            "successRate": round(
                1
                - (
                    self._failed_requests / len(self._request_durations)
                    if self._request_durations
                    else 0.0
                ),
                4,
            ),
        }

    def export_to_csv(self, output_path: str | Path | None = None) -> Path:
        """Write all collected samples to a CSV file."""
        target_path = Path(output_path) if output_path is not None else self.output_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        with target_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.csv_headers)
            writer.writeheader()
            for sample in self._samples:
                writer.writerow(sample.to_row())

        logger.info("Monitoring results written to %s", target_path.relative_to(Path.cwd()))
        return target_path

    def clear(self) -> None:
        """Reset the monitor state."""
        with self._lock:
            self._samples.clear()
            self._request_durations.clear()
            self._resource_usages.clear()
            self._latest_resource_usage = 0.0
            self._failed_requests = 0
