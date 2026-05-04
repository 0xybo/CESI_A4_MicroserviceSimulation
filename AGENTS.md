# AGENTS

Instructions for AI coding agents working in this repository.

## Project Context

- Read [README.md](README.md) first for the research goal, hypotheses, and simulation scope.
- Use [DOCKER_USAGE.md](DOCKER_USAGE.md) for Docker workflow details.
- Use [config-test.json](config-test.json) as the canonical example configuration.

## Quick Start Commands

- Create environment and install deps:
    - `python -m venv .venv`
    - Windows: `.venv\Scripts\activate`
    - `pip install -r requirements.txt`
- Python simulation:
    - `python -m src.Python.main --config config-test.json --requests 200 --workers 2`
- Docker lifecycle via unified CLI:
    - Build: `python -m src build --config config-test.json --output .output`
    - Run generated stack: `python -m src run --output .output`
    - Test generated stack: `python -m src test --output .output --requests 10`
    - Stop generated stack: `python -m src stop --output .output`
- Docker direct CLI (alternative):
    - `python -m src.Docker build --config config-test.json --output .output`

## Architecture Map

- Root entrypoint delegates to [src/**main**.py](src/__main__.py).
- Configuration models and validation live in [src/Config/](src/Config/).
- Core simulation domain lives in [src/Common/](src/Common/):
    - Microservice execution and dependencies: [src/Common/Microservice/](src/Common/Microservice/)
    - Service orchestration: [src/Common/Service/](src/Common/Service/)
    - Container grouping: [src/Common/Container/](src/Common/Container/)
    - Monitoring and metrics: [src/Common/Monitor/](src/Common/Monitor/)
- Runtime implementations:
    - Threaded Python runtime: [src/Python/](src/Python/)
    - Docker runtime and compose generation: [src/Docker/](src/Docker/)

## Conventions

- Keep Python style aligned with [pyproject.toml](pyproject.toml):
    - Black line length: 100
    - Pylint max line length: 100
    - Python target: 3.10+
- Configuration keys are camelCase in JSON and mapped to snake_case model fields via Pydantic aliases.
- Preserve current module boundaries: Config, Common domain, Python runtime, Docker runtime.
- Use existing logger utilities in [src/Common/Utils/logger.py](src/Common/Utils/logger.py).

## Known Pitfalls

- Prefer `python -m src ...` and `python -m src.Python.main ...` for execution. Some older command examples in docs may differ.
- The output/log directories `.output/` and `.logs/` can contain large generated artifacts; avoid broad edits there unless required.
- [pyproject.toml](pyproject.toml) points pytest discovery at `tests`, while this repo currently has `test/`.
- **Configuration validation**: Always use Pydantic models for config loading; manually parsing JSON can bypass validation rules.
- **Microservice dependencies**: Circular dependencies between microservices are not allowed; verify the dependency graph before modifying service definitions.
- **Docker networking**: Services within the same Docker Compose stack communicate via service names (not localhost); ensure container names match config declarations.
- **Monitoring overhead**: High-frequency metric collection can skew performance results; use sampling when needed.

## Agent Workflow

1. Read [README.md](README.md), then inspect [config-test.json](config-test.json).
2. Reproduce behavior with a small run before code changes.
3. Make focused edits in the relevant module area only.
4. Validate with the smallest applicable command from "Quick Start Commands".
5. Keep changes minimal and avoid touching generated output unless the task is about generation/runtime artifacts.

## Common Task Patterns

### Adding a New Metric

1. Define metric collection in [src/Common/Monitor/](src/Common/Monitor/).
2. Hook collection into the runtime lifecycle (Python: [src/Python/main.py](src/Python/main.py); Docker: generate Prometheus config).
3. Update the configuration schema if metric names or units change.
4. Test with `config-test.json` to verify collection without errors.

### Modifying Service Dependencies

1. Update the service definition in the config JSON.
2. Validate dependency graph (no cycles).
3. Test the Python runtime first with small workload: `python -m src.Python.main --config config-test.json --requests 50 --workers 1`
4. Then test Docker: `python -m src build --config config-test.json --output .output && python -m src run --output .output`

### Extending Configuration

1. Add field to Pydantic model in [src/Config/](src/Config/), using snake_case for Python and camelCase alias for JSON.
2. Update validation rules as needed (e.g., min/max values, required fields).
3. Update schema documentation in [Common/Config/schema.json](../../../Common/Config/schema.json) if applicable.
4. Test with a config fixture that exercises the new field.

### Debugging Runtime Issues

1. Check logs in `.logs/` for runtime errors and metric collection issues.
2. For Python: run with `--workers 1` to isolate threading issues.
3. For Docker: use `docker compose logs -f` on the generated compose file to tail container output in real time.
4. Inspect generated Docker Compose file in `.output/` to verify service topology.

## Experimental Context

This simulator is designed to test three hypotheses:

- **H1**: Fine granularity increases inter-service communication, raising latency.
- **H2**: Coarse granularity reduces communication but adds internal complexity.
- **H3**: Medium granularity offers an optimal trade-off.
- **H4**: Containerization deployment strategy impacts scalability and resilience.

Results feed directly into the research paper in [../../Rapport/](../../Rapport/). Keep experimental assumptions clear and reproducible.
