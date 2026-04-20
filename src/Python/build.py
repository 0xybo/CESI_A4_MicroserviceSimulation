"""Build logic for Python platform."""

from pathlib import Path
from src.Python.platform import PythonPlatform


def build(config_path: str | Path = "config-test.json", output_dir: str = ".output") -> None:
    """Build Python execution environment.

    Validates configuration and Python environment.

    Args:
        config_path: Path to configuration file.
        output_dir: Output directory for any generated files (default: .output).

    Raises:
        RuntimeError: If build fails.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    platform = PythonPlatform()
    platform.build(str(config_path), str(output_dir))
