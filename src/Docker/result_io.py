"""I/O and aggregation helpers for Docker result processing."""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ResultMetrics:
    """Aggregated metrics extracted from a single result CSV file."""

    level_key: str
    level_label: str
    request_count: int
    failure_rate_percent: float
    mean_cpu_usage_percent: float
    mean_response_duration_ms: float
    std_failure_rate_percent: float
    std_cpu_usage_percent: float
    std_response_duration_ms: float


def _parse_request_count(csv_path: Path) -> int:
    match = re.search(r"result_(\d+)\.csv$", csv_path.name)
    if not match:
        raise RuntimeError(f"Cannot parse request count from file name: {csv_path.name}")
    return int(match.group(1))


def _parse_level_label(csv_path: Path) -> tuple[str, str]:
    level_dir = csv_path.parent.name
    label = level_dir
    return level_dir, label


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def _read_result_metrics(csv_path: Path) -> ResultMetrics:
    request_count = _parse_request_count(csv_path)
    level_key, level_label = _parse_level_label(csv_path)

    request_durations: list[float] = []
    resource_usages: list[float] = []
    failed_requests = 0

    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            event_type = (row.get("event_type") or "").strip().lower()
            if event_type == "request":
                duration = _parse_float(row.get("request_duration_ms"))
                if duration is not None:
                    request_durations.append(duration)

                failed = (row.get("failed") or "0").strip().lower()
                if failed in {"1", "true", "yes"}:
                    failed_requests += 1
            elif event_type == "resource":
                resource_usage = _parse_float(row.get("resource_usage_percent"))
                if resource_usage is not None:
                    resource_usages.append(resource_usage)

    failure_rate_percent = (
        (failed_requests / len(request_durations)) * 100 if request_durations else 0.0
    )
    mean_cpu_usage_percent = mean(resource_usages) if resource_usages else 0.0
    mean_response_duration_ms = mean(request_durations) if request_durations else 0.0
    # per-file (single-run) standard deviations; use 0.0 when insufficient samples
    std_response_duration_ms = pstdev(request_durations) if len(request_durations) > 0 else 0.0
    std_cpu_usage_percent = pstdev(resource_usages) if len(resource_usages) > 0 else 0.0
    std_failure_rate_percent = 0.0

    return ResultMetrics(
        level_key=level_key,
        level_label=level_label,
        request_count=request_count,
        failure_rate_percent=failure_rate_percent,
        mean_cpu_usage_percent=mean_cpu_usage_percent,
        mean_response_duration_ms=mean_response_duration_ms,
        std_failure_rate_percent=std_failure_rate_percent,
        std_cpu_usage_percent=std_cpu_usage_percent,
        std_response_duration_ms=std_response_duration_ms,
    )


def _aggregate_metrics(
    metrics: list[ResultMetrics],
) -> tuple[dict[str, dict[int, dict[str, float]]], dict[str, str]]:
    grouped: dict[str, dict[int, list[ResultMetrics]]] = defaultdict(lambda: defaultdict(list))
    level_labels: dict[str, str] = {}

    for metric in metrics:
        grouped[metric.level_key][metric.request_count].append(metric)
        level_labels[metric.level_key] = metric.level_label

    aggregated: dict[str, dict[int, dict[str, float]]] = {}
    for level_key, request_groups in grouped.items():
        aggregated[level_key] = {}
        for request_count, samples in request_groups.items():
            aggregated[level_key][request_count] = {
                "failure_rate_percent": mean(sample.failure_rate_percent for sample in samples),
                "std_failure_rate_percent": (
                    pstdev([sample.failure_rate_percent for sample in samples])
                    if len(samples) > 0
                    else 0.0
                ),
                "mean_cpu_usage_percent": mean(sample.mean_cpu_usage_percent for sample in samples),
                "std_cpu_usage_percent": (
                    pstdev([sample.mean_cpu_usage_percent for sample in samples])
                    if len(samples) > 0
                    else 0.0
                ),
                "mean_response_duration_ms": mean(
                    sample.mean_response_duration_ms for sample in samples
                ),
                "std_response_duration_ms": (
                    pstdev([sample.mean_response_duration_ms for sample in samples])
                    if len(samples) > 0
                    else 0.0
                ),
                "sample_count": float(len(samples)),
            }

    return aggregated, level_labels


def _sorted_level_keys(level_keys: Any) -> list[str]:
    return sorted(level_keys, key=_level_sort_key)


def _level_sort_key(level_key: str) -> tuple[int, str]:
    match = re.match(r"^(\d+)_", level_key)
    if match:
        return int(match.group(1)), level_key
    return 10_000, level_key


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return slug.lower() or "plot"
