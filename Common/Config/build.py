from . import SimulationConfig


def build(output: str):
    schema_path = SimulationConfig.generate_schema_file(output)
    print(f"Schema file generated at: {schema_path}")
