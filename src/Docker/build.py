"""Docker Compose file generation for containerized simulations.

This module provides functionality to generate docker-compose.yml files
from simulation configurations for containerized deployment.
"""

from __future__ import annotations

from pathlib import Path
from src.Docker.platform import DockerPlatform
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def build_docker_compose_file(
    config_path: str | Path = "config-test.json", output_dir: str | Path = ".output"
) -> None:
    """Build Docker Compose configuration file.

    Validates Docker environment and generates docker-compose.yml from configuration.

    Args:
        config_path: Path to the simulation configuration.
        output_dir: Output directory where docker-compose.yml will be written (default: .output).

    Raises:
        RuntimeError: If Docker is not available or build fails.
    """
    logger.info(
        "Building Docker Compose configuration: config=%s, output_dir=%s", config_path, output_dir
    )
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Output directory created/verified: %s", output_dir)
    platform = DockerPlatform()
    platform.build(str(config_path), str(output_dir))
    logger.info("Docker Compose build completed successfully")
