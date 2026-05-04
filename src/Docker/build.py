"""Docker Compose build and test facade.

This module re-exports the public functions from the split implementations
so existing imports (from src.Docker.build import ...) keep working.
"""

from __future__ import annotations

from typing import Any

from src.Docker.compose_builder import build_docker_compose_file
from src.Docker.compose_runner import (
    run_docker_compose_file,
    test_docker_compose_file,
    test_all_docker_configs,
    stop_docker_compose_file,
)

__all__ = [
    "build_docker_compose_file",
    "run_docker_compose_file",
    "test_docker_compose_file",
    "test_all_docker_configs",
    "stop_docker_compose_file",
]
