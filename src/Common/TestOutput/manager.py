"""Test output manager for organizing simulation results.

Creates timestamped directories for test runs and manages the organization
of configuration files, generated scripts, and collected metrics.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from src.Config import SimulationConfig
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


class TestOutputManager:
    """Manages test output directory structure and organization.

    Creates timestamped directories in .output with the format:
    .output/<YYYYMMDD_HHMMSS>_<platform>/

    Provides methods to:
    - Create timestamped test directories
    - Store configuration files
    - Generate per-service execution scripts
    - Organize container-specific resources
    - Collect and organize metrics
    """

    def __init__(self, platform_name: str) -> None:
        """Initialize the test output manager.

        Args:
            platform_name: Name of the platform (e.g., "python", "docker").
        """
        self.platform_name = platform_name
        self.test_dir: Path | None = None
        logger.debug(f"TestOutputManager initialized for platform: {platform_name}")

    def create_test_directory(self, base_dir: Path = Path(".output")) -> Path:
        """Create and return a timestamped test directory.

        Creates a new directory with format: <base_dir>/<YYYYMMDD_HHMMSS>_<platform>/

        Args:
            base_dir: Base output directory (default: .output).

        Returns:
            Path to the created test directory.
        """
        logger.debug(f"Creating test directory in: {base_dir}")
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        # Format: YYYYMMDD_HHMMSS_<platform>
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_dir_name = f"{timestamp}_{self.platform_name}"
        self.test_dir = base_dir / test_dir_name

        self.test_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Test directory created: {self.test_dir}")
        return self.test_dir

    def get_test_directory(self) -> Path:
        """Get the current test directory.

        Returns:
            Path to the test directory.

        Raises:
            RuntimeError: If no test directory has been created.
        """
        if self.test_dir is None:
            raise RuntimeError(
                "Test directory not yet created. Call create_test_directory() first."
            )
        return self.test_dir

    def save_config(self, config: SimulationConfig) -> Path:
        """Save the simulation configuration to the test directory.

        Saves config as JSON and returns path.

        Args:
            config: Simulation configuration object.

        Returns:
            Path to the saved config file.

        Raises:
            RuntimeError: If no test directory has been created.
        """
        test_dir = self.get_test_directory()
        config_file = test_dir / "config.json"
        logger.debug(f"Saving configuration to: {config_file}")

        # Convert Pydantic model to dict and save
        config_dict = config.model_dump(by_alias=True)
        config_file.write_text(json.dumps(config_dict, indent=2) + "\n", encoding="utf-8")
        logger.info(f"Configuration saved successfully: {config_file}")

        return config_file

    def create_container_directory(self, container_name: str) -> Path:
        """Create a directory for container-specific resources.

        Args:
            container_name: Name of the container.

        Returns:
            Path to the container directory.

        Raises:
            RuntimeError: If no test directory has been created.
        """
        test_dir = self.get_test_directory()
        container_dir = test_dir / "containers" / container_name
        container_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Container directory created: {container_dir}")
        return container_dir

    def create_service_script(
        self, container_name: str, service_name: str, script_content: str
    ) -> Path:
        """Create a script file for a specific service within a container.

        Args:
            container_name: Name of the container.
            service_name: Name of the service.
            script_content: Content of the script.

        Returns:
            Path to the created script file.
        """
        container_dir = self.create_container_directory(container_name)
        script_file = container_dir / f"{service_name}.py"
        logger.debug(f"Creating service script: {script_file}")
        script_file.write_text(script_content, encoding="utf-8")
        logger.debug(f"Service script created: {script_file}")
        return script_file

    def save_results(self, results: dict[str, Any]) -> Path:
        """Save execution results to the test directory.

        Args:
            results: Execution results dictionary.

        Returns:
            Path to the saved results file.

        Raises:
            RuntimeError: If no test directory has been created.
        """
        test_dir = self.get_test_directory()
        results_file = test_dir / "results.json"

        results_file.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        return results_file

    def get_metrics_directory(self) -> Path:
        """Get or create the metrics directory for the test.

        Returns:
            Path to the metrics directory.

        Raises:
            RuntimeError: If no test directory has been created.
        """
        test_dir = self.get_test_directory()
        metrics_dir = test_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        return metrics_dir

    def save_metrics(self, metrics: list[dict[str, Any]], filename: str = "metrics.json") -> Path:
        """Save collected metrics to the metrics directory.

        Args:
            metrics: List of metric dictionaries.
            filename: Filename for metrics (default: metrics.json).

        Returns:
            Path to the saved metrics file.
        """
        metrics_dir = self.get_metrics_directory()
        metrics_file = metrics_dir / filename

        metrics_file.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        return metrics_file

    def cleanup_test_directory(self) -> None:
        """Remove the current test directory (useful for rollback).

        Raises:
            RuntimeError: If no test directory has been created.
        """
        test_dir = self.get_test_directory()
        if test_dir.exists():
            shutil.rmtree(test_dir)
        self.test_dir = None
