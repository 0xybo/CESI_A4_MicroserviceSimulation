# AI Agent Instructions for MicroserviceSimulation

## Project Overview

This project simulates distributed microservices architectures to study the impact of service granularity and containerization on system performance. It's an educational tool for a scientific approach course.

**Research Question**: How does varying the granularity level of microservices and their containerized deployment affect the performance metrics (latency, response time, load) of a distributed application?

**Key Scenarios Tested**:

- Granularity levels: Fine (many microservices), Medium (balanced), Coarse (monolithic)
- Deployment: Single container, container per service group, or container per microservice

## Architecture

```
Microservice (smallest unit)
    ↓ (many per Service)
Service (functional unit)
    ↓ (many per Container)
Container (deployment unit)
```

### Core Components

| Module                                                 | Purpose                                                                          |
| ------------------------------------------------------ | -------------------------------------------------------------------------------- |
| [Common/Config](Common/Config/)                        | **Config system**: Pydantic models for configuration, CLI parser, config loading |
| [Common/Microservice](Common/Microservice/__main__.py) | Simulates individual microservice units with error rates, dependencies, delays   |
| [Common/Service](Common/Service/__main__.py)           | Groups microservices into services                                               |
| [Common/Container](Common/Container/__main__.py)       | Manages service execution and resource boundaries                                |
| [Python/main.py](Python/main.py)                       | Python thread-based simulation executor using ThreadPoolExecutor                 |
| [Docker/build.py](Docker/build.py)                     | Generates docker-compose files for containerized simulations                     |

## Configuration System

### File Format

- **Location**: `config.json` (default) or specified via CLI `--input`
- **Format**: JSON with camelCase keys (converted to snake_case in Python via Pydantic aliases)
- **Example**: `"callRate"` in JSON → `call_rate` in Python

### Key Config Structure

```
SimulationConfig
├── microservices: dict[ConfigKey, MicroserviceConfig]
│   ├── dependencies: dict[ConfigKey, DependencyConfig]
│   ├── errorRate: float (0-1)
│   ├── workDifficulty: float (0+)
│   └── delay: int (ms)
├── services: dict[ConfigKey, ServiceConfig]
│   └── microservices: dict[ConfigKey, ServiceMicroserviceConfig]
│       └── canRestart: bool
└── containers: dict[ConfigKey, ContainerServiceConfig]
    └── canRestart: bool
```

### Validation Rules

- `ConfigKey`: Must match pattern `^[a-zA-Z0-9_]+$` (alphanumeric + underscore)
- Rates (`callRate`, `errorRate`): 0-1 (decimal)
- `workDifficulty`: Non-negative
- `delay`: Non-negative milliseconds

See [config-test.json](config-test.json) for examples.

## Common Commands

### View Configuration Schema

```bash
python -m . config --output .
```

Generates JSON schema for validation and documentation.

### Parse & Validate Configuration

```bash
python -m . config --input config.json
```

Validates and prints parsed configuration.

### Build Simulation Environment

```bash
python -m . build python      # Build Python thread-based simulation
python -m . build docker      # Build Docker Compose configuration
python -m . build             # Build both
```

## Python Simulation Execution

Entry point: [Python/main.py](Python/main.py)

**Key Functions**:

- `build_runtime()`: Creates Microservice, Service, Container instances from config
- `run_single_container()`: Executes simulation for one container with ThreadPoolExecutor
- Returns JSON output with execution times and service metrics

**Execution Flow**:

1. Load config from JSON
2. Build runtime objects (Microservices, Services, Containers)
3. Execute each container in parallel threads
4. Collect performance metrics (elapsed time, microservice results)

## Development Conventions

### Code Style

- **Imports**: Use `from __future__ import annotations` for forward references
- **Naming**: snake_case for Python, camelCase for JSON
- **Models**: Pydantic BaseModel with `model_config = ConfigDict(populate_by_name=True)`
- **Aliasing**: Use `alias="camelCaseKey"` in Pydantic Field for JSON compatibility
- **Constraints**: Use Pydantic validators (StringConstraints, Field validators)

### Error Handling

- Use [Common/Utils/error.py](Common/Utils/error.py):`print_error(message)` for error reporting
- Exits with code 1 on failure

### File Organization

- `__main__.py` files contain main class/logic per module
- `cli.py` handles argument parsing
- `build.py` handles build/compilation logic
- `__init__.py` exports public interfaces

## Common Development Tasks

### Adding a New Configuration Parameter

1. Update Pydantic model in [Common/Config/**init**.py](Common/Config/__init__.py)
2. Add Field with validation and camelCase alias
3. Test with `python -m . config --input config.json`
4. Update schema documentation

### Implementing Python Simulation

1. Modify [Python/main.py](Python/main.py)
2. Implement `build_runtime()` to instantiate from config
3. Implement `run_single_container()` to execute simulation
4. Return results as dict/JSON

### Generating Docker Compose

1. Implement [Docker/build.py](Docker/build.py):`build_docker_compose_file(config, output)`
2. Generate docker-compose.yml from config hierarchy
3. Map containers → services → microservices

## Key Files to Understand

| File                                 | Purpose                                   |
| ------------------------------------ | ----------------------------------------- |
| [README.md](README.md)               | Research hypotheses and experiment design |
| [config-test.json](config-test.json) | Example configuration file                |
| [requirements.txt](requirements.txt) | Python dependencies (pydantic)            |
| [**main**.py](__main__.py)           | CLI entry point                           |

## Notes for AI Agents

- **Configuration-First Design**: All simulation behavior is driven by JSON config
- **WIP**: `Python/build.py` and full `Docker/build.py` are incomplete—focus on feature development
- **Pydantic Best Practice**: Always use aliases for JSON compatibility
- **Testing**: Use `config-test.json` as a reference for valid configurations
- **Performance Tracking**: Simulation captures elapsed time; ensure timing measurements are accurate
