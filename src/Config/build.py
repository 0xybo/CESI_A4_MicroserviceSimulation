"""Schema file generation for simulation configurations."""

from pathlib import Path
from src.Common.Utils.logger import get_logger
from . import SimulationConfig

logger = get_logger(__name__)


def build(output: str | None = None) -> None:
    """Generate and write the simulation configuration schema.

    Args:
        output: Directory path where schema.json will be created (default: .output).
    """
    logger.info("Generating simulation configuration schema to directory: %s", output)
    if output is None:
        output = ".output"
        logger.debug("Using default output directory: .output")
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Output directory created/verified: %s", output_dir)
    try:
        schema_path = SimulationConfig.generate_schema_file(output_dir)
        logger.info("Schema file generated successfully at: %s", schema_path)
    except Exception as e:
        logger.error("Failed to generate schema: %s", e, exc_info=True)
        raise
