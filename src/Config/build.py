"""Schema file generation for simulation configurations."""

from pathlib import Path
from . import SimulationConfig


def build(output: str = None) -> None:
    """Generate and write the simulation configuration schema.

    Args:
        output: Directory path where schema.json will be created (default: .output).
    """
    if output is None:
        output = ".output"
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)
    schema_path = SimulationConfig.generate_schema_file(output_dir)
    print(f"Schema file generated at: {schema_path}")
