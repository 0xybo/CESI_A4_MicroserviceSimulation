"""Table printing and CSV export for Docker results."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from src.Common.Utils.logger import get_logger
from src.Docker import result_io

logger = get_logger(__name__)


def _format_cell(mean_val: float, std_val: float, samples: float) -> str:
    """Format a table cell as 'mean (std) [n]'."""
    if math.isnan(mean_val):
        return "-"
    return f"{mean_val:.3f} ({std_val:.3f}) [{int(samples)}]"


def print_docker_results(
    output_dir: str | Path = ".output", output_file: str | Path | None = None, color: bool = True
) -> None:
    """Print three tables (failure, CPU, response) with values per level and request count.

    Args:
        output_dir: Root output directory containing result CSVs.
        output_file: Optional path to write the plain-text tables. Defaults to
            <output_dir>/results_tables.txt.
        color: Enable ANSI colors for terminal output. File output is always plain text.

    The tables show mean (std) [sample_count] for each cell.
    """
    output_root = Path(output_dir)
    if not output_root.exists():
        raise RuntimeError(f"Output directory not found: {output_root}")

    result_files = sorted(output_root.rglob("result_*.csv"))
    if not result_files:
        raise RuntimeError(f"No result_*.csv files found under {output_root}")

    metrics = [result_io._read_result_metrics(csv_path) for csv_path in result_files]
    aggregated, level_labels = result_io._aggregate_metrics(metrics)

    # Determine all request counts present across levels
    all_request_counts = sorted({rc for level in aggregated.values() for rc in level.keys()})

    # Prepare three tables
    tables = [
        ("failure_rate_percent", "Failure (%)", "std_failure_rate_percent"),
        ("mean_cpu_usage_percent", "Mean CPU (%)", "std_cpu_usage_percent"),
        ("mean_response_duration_ms", "Mean response duration (ms)", "std_response_duration_ms"),
    ]

    # Precompute rows for all tables so we can align columns across tables
    header = ["Level"] + [str(rc) for rc in all_request_counts]
    # all_tables_rows: list of tables -> list of rows -> list of cells
    # each cell for columns >0 is a tuple (mean_str, std_str, count_str)
    all_tables_rows: list[list[list[tuple[str, str, str] | str]]] = []
    for key, title, std_key in tables:
        rows: list[list[tuple[str, str, str] | str]] = []
        for level_key in result_io._sorted_level_keys(aggregated.keys()):
            row: list[tuple[str, str, str] | str] = [level_labels.get(level_key, level_key)]
            for rc in all_request_counts:
                cell_data = aggregated.get(level_key, {}).get(rc, None)
                if cell_data is None:
                    row.append(("-", "-", "-"))
                else:
                    mean_val = cell_data.get(key, math.nan)
                    std_val = cell_data.get(std_key, 0.0)
                    samples = int(cell_data.get("sample_count", 0))
                    if isinstance(mean_val, float) and not math.isnan(mean_val):
                        mean_s = f"{mean_val:,.3f}"
                        std_s = f"{std_val:,.3f}"
                        count_s = str(samples)
                    else:
                        mean_s = "-"
                        std_s = "-"
                        count_s = "-"
                    row.append((mean_s, std_s, count_s))
            rows.append(row)
        all_tables_rows.append(rows)

    # Determine global column widths across all tables for mean/std/count parts
    cols = len(header)
    # col0 (Level) width
    col0_width = max(len(header[0]), *(len(row[0]) for rows in all_tables_rows for row in rows))
    mean_w = [0] * (cols - 1)
    std_w = [0] * (cols - 1)
    cnt_w = [0] * (cols - 1)
    for col_idx in range(1, cols):
        for rows in all_tables_rows:
            for row in rows:
                cell = row[col_idx]
                if isinstance(cell, tuple):
                    m, s, c = cell
                    mean_w[col_idx - 1] = max(mean_w[col_idx - 1], len(m))
                    std_w[col_idx - 1] = max(std_w[col_idx - 1], len(s))
                    cnt_w[col_idx - 1] = max(cnt_w[col_idx - 1], len(c))
                else:
                    mean_w[col_idx - 1] = max(mean_w[col_idx - 1], len(str(cell)))

    # Compute total widths per column (including separators ' (' ') [' ']') => 6 extra chars
    total_col_w = [col0_width] + [mean_w[i] + std_w[i] + cnt_w[i] + 6 for i in range(cols - 1)]

    # ANSI color sequences (background for alternating rows)
    ANSI_RESET = "\x1b[0m"
    ANSI_BG = "\x1b[48;5;236m"  # dark gray background

    # Prepare output file path
    out_path = None
    if output_file is None:
        out_path = Path(output_dir) / "results_tables.txt"
    else:
        out_path = Path(output_file)

    out_lines: list[str] = []

    # CSV export directory
    csv_dir = out_path.parent
    csv_dir.mkdir(parents=True, exist_ok=True)

    # Print each table using the same column widths with aligned mean/std/count
    for (key, title, std_key), rows in zip(tables, all_tables_rows):
        # Separation: blank line before table
        print()
        out_lines.append("")

        # Title
        print(title)
        out_lines.append(title)

        # Header
        header_cells = [header[0].center(total_col_w[0])] + [
            header[i].center(total_col_w[i]) for i in range(1, cols)
        ]
        header_line = " | ".join(header_cells)
        print(header_line)
        out_lines.append(header_line)

        total_width = sum(total_col_w) + 3 * (cols - 1)
        sep_line = "-" * total_width
        print(sep_line)
        out_lines.append(sep_line)

        # Prepare CSV file for this table
        csv_path = csv_dir / f"{key}_table.csv"
        try:
            import csv as _csv

            with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = _csv.writer(csv_file)
                writer.writerow(["Level"] + [str(rc) for rc in all_request_counts])

                # Rows
                for row_idx, row in enumerate(rows):
                    # CSV cells (plain) and display cells (padded/aligned)
                    csv_cells = [str(row[0])]
                    display_cells = [str(row[0]).ljust(total_col_w[0])]

                    for i in range(1, cols):
                        cell = row[i]
                        if isinstance(cell, tuple):
                            m, s, c = cell
                            mw = mean_w[i - 1]
                            sw = std_w[i - 1]
                            cw = cnt_w[i - 1]
                            csv_text = f"{m} ({s}) [{c}]"
                            disp_text = f"{m.rjust(mw)} ({s.rjust(sw)}) [{c.rjust(cw)}]"
                        else:
                            csv_text = str(cell)
                            disp_text = str(cell).center(total_col_w[i])

                        csv_cells.append(csv_text)
                        display_cells.append(disp_text)

                    line = " | ".join(display_cells)
                    # Append to plain-text collector
                    out_lines.append(line)

                    # write CSV row (level + cell_text per column)
                    writer.writerow(csv_cells)

                    # Print colored to terminal if requested
                    if color:
                        if row_idx % 2 == 0:
                            print(f"{ANSI_BG}{line}{ANSI_RESET}")
                        else:
                            print(line)
                    else:
                        print(line)

        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to write CSV for table %s: %s", key, csv_path)

        # Separation: blank line after table
        print()
        out_lines.append("")

    # Write plain text to file (no ANSI)
    try:
        out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        logger.info("Printed tables saved to %s", out_path)
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to write result tables to file: %s", out_path)
