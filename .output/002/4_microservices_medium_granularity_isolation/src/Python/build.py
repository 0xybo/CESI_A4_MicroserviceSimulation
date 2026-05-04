"""Build logic for Python platform."""

from pathlib import Path
from src.Python.platform import PythonPlatform
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def build(config_path: str | Path = "config-test.json", output_dir: str = ".output") -> None:
    """Build Python execution environment.

    Validates configuration and Python environment.

    Args:
        config_path: Path to configuration file.
        output_dir: Output directory for any generated files (default: .output).

    Raises:
        RuntimeError: If build fails.
    """
    logger.info(f"Building Python platform: config={config_path}, output_dir={output_dir}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Output directory created/verified: {output_dir}")
    platform = PythonPlatform()
    platform.build(str(config_path), str(output_dir))
    logger.info("Python platform build completed successfully")
