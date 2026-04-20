"""Docker Compose file generation for containerized simulations.

This module provides functionality to generate docker-compose.yml files
from simulation configurations for containerized deployment.
"""

from __future__ import annotations

from pathlib import Path
from src.Docker.platform import DockerPlatform


def build_docker_compose_file(
    config_path: str | Path = "config-test.json", output_dir: str = ".output"
) -> None:
    """Build Docker Compose configuration file.

    Validates Docker environment and generates docker-compose.yml from configuration.

    Args:
        config_path: Path to the simulation configuration.
        output_dir: Output directory where docker-compose.yml will be written (default: .output).

    Raises:
        RuntimeError: If Docker is not available or build fails.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    platform = DockerPlatform()
    platform.build(str(config_path), str(output_dir))
