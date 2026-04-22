"""Abstract Platform class for simulation execution.

Provides a unified interface for different execution backends (Python, Docker, etc.)
to build environments and execute simulations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

from src.Common.TestOutput import TestOutputManager


class Platform(ABC):
    """Abstract base class for simulation execution platforms.

    A platform provides methods to build a simulation environment and execute
    it, abstracting away the differences between local Python execution,
    Docker-based execution, and potentially other backends.
    """

    def __init__(self) -> None:
        """Initialize the platform instance."""
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.output_manager: TestOutputManager | None = None

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name/identifier of this platform.

        Returns:
            Platform identifier (e.g., "python", "docker").
        """

    @abstractmethod
    def build(self, config_path: str, output_dir: str | None = None) -> None:
        """Build and prepare the simulation environment.

        This phase validates dependencies, generates configuration files,
        or prepares containers as needed by the specific platform.

        Creates a timestamped test directory in <output_dir>/<YYYYMMDD_HHMMSS>_<platform>/
        where all test artifacts will be stored.

        Args:
            config_path: Path to the simulation configuration file.
            output_dir: Base directory for test output (default: .output).
                        Timestamped subdirectory will be created within this.

        Raises:
            RuntimeError: If platform requirements are not met.
            FileNotFoundError: If config file doesn't exist.
        """

    @abstractmethod
    def execute(
        self,
        config_path: str,
        request_count: int,
        output_file: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute the simulation.

        Args:
            config_path: Path to the simulation configuration file.
            request_count: Number of requests to simulate.
            output_file: Optional path to write results to.
            **kwargs: Platform-specific execution options.

        Returns:
            Dictionary containing execution results with structure:
            {
                "platform": str,
                "totalElapsedMs": float,
                "containers": [
                    {
                        "container": str,
                        "elapsedMs": float,
                        "services": [...],
                        "microservices": {...}
                    }
                ]
            }

        Raises:
            RuntimeError: If execution fails.
        """

    def initialize_output_manager(self, base_output_dir: str | Path | None = None) -> Path:
        """Initialize the test output manager and create timestamped directory.

        Args:
            base_output_dir: Base directory for output (default: .output).

        Returns:
            Path to the created timestamped test directory.
        """
        if base_output_dir is None:
            base_output_dir = ".output"

        self.output_manager = TestOutputManager(self.get_platform_name())
        test_dir = self.output_manager.create_test_directory(Path(base_output_dir))
        return test_dir

    def get_test_output_directory(self) -> Path:
        """Get the current test output directory.

        Returns:
            Path to the test directory.

        Raises:
            RuntimeError: If output manager not initialized.
        """
        if self.output_manager is None:
            raise RuntimeError(
                "Output manager not initialized. Call initialize_output_manager() first."
            )
        return self.output_manager.get_test_directory()

    def cleanup(self) -> None:
        """Clean up resources after execution.

        This is optional and can be overridden by subclasses.
        Default implementation does nothing.
        """

    def record_timing(self) -> None:
        """Record start time of execution."""
        self.start_time = datetime.now()

    def complete_timing(self) -> None:
        """Record end time of execution."""
        self.end_time = datetime.now()

    def get_execution_duration_ms(self) -> float:
        """Get total execution duration in milliseconds.

        Returns:
            Duration in milliseconds, or 0 if timing not set.
        """
        if self.start_time is None or self.end_time is None:
            return 0.0
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000
