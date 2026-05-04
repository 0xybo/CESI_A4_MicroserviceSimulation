"""Facade for result plotting and table printing.

This module re-exports the public functions from the split implementations
so existing imports (from src.Docker.result_plots import ...) keep working.
"""

from __future__ import annotations

from pathlib import Path

from src.Common.Utils.logger import get_logger
from src.Docker.result_table import print_docker_results
from src.Docker.result_plotting import plot_docker_results

logger = get_logger(__name__)

__all__ = ["print_docker_results", "plot_docker_results"]
