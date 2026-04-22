"""Schema file generation for simulation configurations."""

from pathlib import Path
from . import SimulationConfig
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def build(output: str = None) -> None:
    """Generate and write the simulation configuration schema.

    Args:
        output: Directory path where schema.json will be created (default: .output).
    """
    logger.info(f"Generating simulation configuration schema to directory: {output}")
    if output is None:
        output = ".output"
        logger.debug("Using default output directory: .output")
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Output directory created/verified: {output_dir}")
    try:
        schema_path = SimulationConfig.generate_schema_file(output_dir)
        logger.info(f"Schema file generated successfully at: {schema_path}")
        print(f"Schema file generated at: {schema_path}")
    except Exception as e:
        logger.error(f"Failed to generate schema: {e}", exc_info=True)
        raise
