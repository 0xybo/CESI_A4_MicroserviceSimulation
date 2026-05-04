"""Plot Docker simulation results from generated result CSV files."""

from __future__ import annotations

import csv
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from matplotlib import pyplot as plt

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


def plot_docker_results(
    output_dir: str | Path = ".output",
    plot_type: str = "line",
    plots_dir: str | Path | None = None,
) -> list[Path]:
    """Create plots from every result_<count>.csv file under output_dir.

    Args:
        output_dir: Root directory containing generated architecture folders.
        plot_type: Either "line" or "bar".
        plots_dir: Directory where images will be written.

    Returns:
        The list of generated image paths.
    """
    output_root = Path(output_dir)
    if not output_root.exists():
        raise RuntimeError(f"Output directory not found: {output_root}")

    result_files = sorted(output_root.rglob("result_*.csv"))
    if not result_files:
        raise RuntimeError(f"No result_*.csv files found under {output_root}")

    metrics = [_read_result_metrics(csv_path) for csv_path in result_files]
    aggregated, level_labels = _aggregate_metrics(metrics)

    target_dir = Path(plots_dir) if plots_dir is not None else output_root / "plots"
    target_dir.mkdir(parents=True, exist_ok=True)

    plot_type = plot_type.lower().strip()
    if plot_type == "line":
        generated = _generate_line_plots(aggregated, level_labels, target_dir)
    elif plot_type == "bar":
        generated = _generate_bar_plots(aggregated, level_labels, target_dir)
    else:
        raise ValueError("plot_type must be either 'line' or 'bar'")

    logger.info("Generated %d plot(s) in %s", len(generated), target_dir)
    return generated


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


def _generate_line_plots(
    aggregated: dict[str, dict[int, dict[str, float]]],
    level_labels: dict[str, str],
    target_dir: Path,
) -> list[Path]:
    generated: list[Path] = []
    for level_key in _sorted_level_keys(aggregated.keys()):
        request_counts = sorted(aggregated[level_key].keys())
        if not request_counts:
            continue

        metrics_by_request = [
            aggregated[level_key][request_count] for request_count in request_counts
        ]
        level_label = level_labels.get(level_key, level_key)

        fig, ax_left = plt.subplots(figsize=(11, 6))
        ax_right = ax_left.twinx()

        failure_vals = [item["failure_rate_percent"] for item in metrics_by_request]
        failure_stds = [item.get("std_failure_rate_percent", 0.0) for item in metrics_by_request]
        failure_line = ax_left.plot(
            request_counts,
            failure_vals,
            marker="o",
            label="Failure (%)",
            color="tab:red",
        )
        ax_left.fill_between(
            request_counts,
            [v - s for v, s in zip(failure_vals, failure_stds)],
            [v + s for v, s in zip(failure_vals, failure_stds)],
            color="tab:red",
            alpha=0.15,
        )

        cpu_vals = [item["mean_cpu_usage_percent"] for item in metrics_by_request]
        cpu_stds = [item.get("std_cpu_usage_percent", 0.0) for item in metrics_by_request]
        cpu_line = ax_left.plot(
            request_counts,
            cpu_vals,
            marker="o",
            label="Mean CPU usage (%)",
            color="tab:blue",
        )
        ax_left.fill_between(
            request_counts,
            [v - s for v, s in zip(cpu_vals, cpu_stds)],
            [v + s for v, s in zip(cpu_vals, cpu_stds)],
            color="tab:blue",
            alpha=0.12,
        )

        resp_vals = [item["mean_response_duration_ms"] for item in metrics_by_request]
        resp_stds = [item.get("std_response_duration_ms", 0.0) for item in metrics_by_request]
        response_line = ax_right.plot(
            request_counts,
            resp_vals,
            marker="o",
            label="Mean response duration (ms)",
            color="tab:green",
        )
        ax_right.fill_between(
            request_counts,
            [v - s for v, s in zip(resp_vals, resp_stds)],
            [v + s for v, s in zip(resp_vals, resp_stds)],
            color="tab:green",
            alpha=0.12,
        )

        ax_left.set_title(f"{level_label} - metrics by request count")
        ax_left.set_xlabel("Request count")
        ax_left.set_ylabel("Failure / CPU usage (%)")
        ax_right.set_ylabel("Mean response duration (ms)")
        # Use a logarithmic x-axis for request counts
        ax_left.set_xscale("log")
        ax_left.set_xticks(request_counts)
        ax_left.set_xticklabels([str(rc) for rc in request_counts])
        ax_left.grid(True, alpha=0.3)

        lines = failure_line + cpu_line + response_line
        labels = [str(line.get_label()) for line in lines]
        ax_left.legend(lines, labels, loc="upper left")

        output_path = target_dir / f"line_{_slugify(level_label)}.png"
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        generated.append(output_path)

    return generated


def _generate_bar_plots(
    aggregated: dict[str, dict[int, dict[str, float]]],
    level_labels: dict[str, str],
    target_dir: Path,
) -> list[Path]:
    generated: list[Path] = []
    level_keys = _sorted_level_keys(aggregated.keys())
    request_counts = sorted(
        {request_count for data in aggregated.values() for request_count in data}
    )

    metrics = [
        ("failure_rate_percent", "Failure (%)", "bar_failure_rate.png"),
        ("mean_cpu_usage_percent", "Mean CPU usage (%)", "bar_mean_cpu_usage.png"),
        (
            "mean_response_duration_ms",
            "Mean response duration (ms)",
            "bar_mean_response_duration.png",
        ),
    ]

    for metric_key, metric_label, filename in metrics:
        fig, ax = plt.subplots(figsize=(12, 6))
        group_width = 0.8
        bar_width = group_width / max(len(level_keys), 1)
        base_positions = list(range(len(request_counts)))

        for index, level_key in enumerate(level_keys):
            values = [
                aggregated.get(level_key, {}).get(request_count, {}).get(metric_key, math.nan)
                for request_count in request_counts
            ]
            # map metric_key to the corresponding std key in aggregated
            if metric_key == "failure_rate_percent":
                std_key = "std_failure_rate_percent"
            elif metric_key == "mean_cpu_usage_percent":
                std_key = "std_cpu_usage_percent"
            elif metric_key == "mean_response_duration_ms":
                std_key = "std_response_duration_ms"
            else:
                std_key = ""

            stds = [
                aggregated.get(level_key, {}).get(request_count, {}).get(std_key, 0.0)
                for request_count in request_counts
            ]

            offsets = [
                position - group_width / 2 + (index + 0.5) * bar_width
                for position in base_positions
            ]
            ax.bar(
                offsets,
                values,
                width=bar_width,
                label=level_labels.get(level_key, level_key),
                yerr=stds,
                capsize=4,
            )

        ax.set_title(f"{metric_label} by request count")
        ax.set_xlabel("Request count")
        ax.set_ylabel(metric_label)
        ax.set_xticks(base_positions)
        ax.set_xticklabels([str(request_count) for request_count in request_counts])
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(ncol=2)

        output_path = target_dir / filename
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        generated.append(output_path)

    return generated


def _parse_request_count(csv_path: Path) -> int:
    match = re.search(r"result_(\d+)\.csv$", csv_path.name)
    if not match:
        raise RuntimeError(f"Cannot parse request count from file name: {csv_path.name}")
    return int(match.group(1))


def _parse_level_label(csv_path: Path) -> tuple[str, str]:
    level_dir = csv_path.parent.name
    # if "_" in level_dir:
    #     _, label = level_dir.split("_", 1)
    # else:
    #     label = level_dir
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
