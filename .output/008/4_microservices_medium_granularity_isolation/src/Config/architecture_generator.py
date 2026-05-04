"""Generate families of simulation configurations from dependency permutations."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from src.Common.Utils.logger import get_logger

from .container_config import ContainerConfig
from .container_service_config import ContainerServiceConfig
from .dependency_config import DependencyConfig
from .microservice_config import MicroserviceConfig
from .service_config import ServiceConfig
from .service_microservice_config import ServiceMicroserviceConfig
from .simulation_config import SimulationConfig

logger = get_logger(__name__)

MICROSERVICE_NAMES: tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(12))
REFERENCE_EDGE_COUNT = 15
DEFAULT_REQUEST_COUNT = 100
DEFAULT_LOG_LEVEL = "DEBUG"
DEFAULT_CPU_LIMIT = 0.5


@dataclass(frozen=True)
class LevelDefinition:
    """Deployment layout for one of the six configuration levels."""

    folder_name: str
    service_groups: tuple[tuple[str, tuple[str, ...]], ...]
    container_groups: tuple[tuple[str, tuple[str, ...]], ...]


LEVEL_1_MONOLITHIC = LevelDefinition(
    folder_name="1_monolithic",
    service_groups=(("ServiceA", MICROSERVICE_NAMES),),
    container_groups=(("ContainerA", ("ServiceA",)),),
)

LEVEL_2_MEDIUM = LevelDefinition(
    folder_name="2_microservices_medium_granularity",
    service_groups=(
        ("ServiceA", ("A",)),
        ("ServiceB", ("B", "C", "H")),
        ("ServiceC", ("G", "I", "J", "D")),
        ("ServiceD", ("E", "F", "K", "L")),
    ),
    container_groups=(("ContainerA", ("ServiceA", "ServiceB", "ServiceC", "ServiceD")),),
)

LEVEL_3_FINE = LevelDefinition(
    folder_name="3_microservices_fine_granularity",
    service_groups=tuple((f"Service{name}", (name,)) for name in MICROSERVICE_NAMES),
    container_groups=(("ContainerA", tuple(f"Service{name}" for name in MICROSERVICE_NAMES)),),
)

LEVEL_4_MEDIUM_ISOLATION = LevelDefinition(
    folder_name="4_microservices_medium_granularity_isolation",
    service_groups=LEVEL_2_MEDIUM.service_groups,
    container_groups=tuple(
        (f"Container{suffix}", (service_name,))
        for suffix, (service_name, _) in zip("ABCD", LEVEL_2_MEDIUM.service_groups)
    ),
)

LEVEL_5_FINE_MEDIUM_ISOLATION = LevelDefinition(
    folder_name="5_microservices_fine_granularity_isolation",
    service_groups=LEVEL_3_FINE.service_groups,
    container_groups=(
        ("ContainerA", ("ServiceA",)),
        ("ContainerB", ("ServiceB", "ServiceC", "ServiceH")),
        ("ContainerC", ("ServiceG", "ServiceI", "ServiceJ", "ServiceD")),
        ("ContainerD", ("ServiceE", "ServiceF", "ServiceK", "ServiceL")),
    ),
)

LEVEL_6_FINE_HIGH_ISOLATION = LevelDefinition(
    folder_name="6_microservices_fine_granularity_high_isolation",
    service_groups=LEVEL_3_FINE.service_groups,
    container_groups=tuple(
        (f"Container{name}", (f"Service{name}",)) for name in MICROSERVICE_NAMES
    ),
)

LEVEL_DEFINITIONS: tuple[LevelDefinition, ...] = (
    LEVEL_1_MONOLITHIC,
    LEVEL_2_MEDIUM,
    LEVEL_3_FINE,
    LEVEL_4_MEDIUM_ISOLATION,
    LEVEL_5_FINE_MEDIUM_ISOLATION,
    LEVEL_6_FINE_HIGH_ISOLATION,
)


def generate_architecture_configs(
    count: int,
    output_root: str | Path = ".output",
    seed: int | None = None,
) -> list[Path]:
    """Generate ``count`` architecture families and write six config levels for each.

    The generator keeps the 12 microservice names fixed and rewires dependency
    relations while preserving a reachable acyclic graph rooted at ``A``.
    """

    if count < 1:
        raise ValueError("count must be greater than 0")

    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)

    architecture_start_id = _next_architecture_id(output_path)
    random_source = random.Random(seed)

    written_files: list[Path] = []

    for architecture_index in range(count):
        architecture_id = architecture_start_id + architecture_index
        microservice_dependencies = _generate_dependency_graph(random_source)

        for level_definition in LEVEL_DEFINITIONS:
            level_output_dir = output_path / f"{architecture_id:03d}" / level_definition.folder_name
            level_output_dir.mkdir(parents=True, exist_ok=True)

            config = _build_simulation_config(microservice_dependencies, level_definition)
            payload = config.model_dump(by_alias=True)
            payload["entrypoint"] = "ServiceA"

            config_path = level_output_dir / "config.json"
            config_path.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")
            readme_path = level_output_dir / "README.md"
            readme_path.write_text(
                _render_level_readme(
                    architecture_id=architecture_id,
                    level_definition=level_definition,
                    microservice_dependencies=microservice_dependencies,
                ),
                encoding="utf-8",
            )
            written_files.append(config_path)

            logger.info("Generated architecture %s at %s", architecture_id, config_path)

    return written_files


def _next_architecture_id(output_root: Path) -> int:
    numeric_ids: list[int] = []
    for child in output_root.iterdir():
        if not child.is_dir():
            continue
        try:
            numeric_ids.append(int(child.name))
        except ValueError:
            continue
    return max(numeric_ids, default=0) + 1


def _generate_dependency_graph(rng: random.Random) -> dict[str, dict[str, DependencyConfig]]:
    """Create a reachable acyclic dependency graph rooted at ``A``."""

    ordered_microservices = list(MICROSERVICE_NAMES)
    tail_microservices = ordered_microservices[1:]
    rng.shuffle(tail_microservices)
    execution_order = [ordered_microservices[0], *tail_microservices]

    dependencies: dict[str, dict[str, DependencyConfig]] = {name: {} for name in MICROSERVICE_NAMES}
    existing_edges: set[tuple[str, str]] = set()

    for target_index, target_name in enumerate(execution_order[1:], start=1):
        predecessor_candidates = execution_order[:target_index]
        source_name = rng.choice(predecessor_candidates)
        dependencies[source_name][target_name] = DependencyConfig(call_rate=1.0, stop_on_error=True)
        existing_edges.add((source_name, target_name))

    remaining_edges = REFERENCE_EDGE_COUNT - (len(execution_order) - 1)
    while remaining_edges > 0:
        source_index = rng.randrange(0, len(execution_order) - 1)
        source_name = execution_order[source_index]
        candidate_targets = [
            name
            for name in execution_order[source_index + 1 :]
            if (source_name, name) not in existing_edges
        ]
        if not candidate_targets:
            continue

        target_name = rng.choice(candidate_targets)
        dependencies[source_name][target_name] = DependencyConfig(
            call_rate=1.0, stop_on_error=False
        )
        existing_edges.add((source_name, target_name))
        remaining_edges -= 1

    return {source: dict(sorted(targets.items())) for source, targets in dependencies.items()}


def _build_simulation_config(
    microservice_dependencies: dict[str, dict[str, DependencyConfig]],
    level_definition: LevelDefinition,
) -> SimulationConfig:
    microservice_to_service = {
        microservice_name: service_name
        for service_name, microservices in level_definition.service_groups
        for microservice_name in microservices
    }

    microservices = {
        microservice_name: MicroserviceConfig(
            dependencies=microservice_dependencies[microservice_name],
            error_rate=0.0,
            work_difficulty=1,
            delay_ms=0,
        )
        for microservice_name in MICROSERVICE_NAMES
    }

    services = {
        service_name: ServiceConfig(
            entrypoint=microservices_in_service[0],
            dependencies={},
            microservices={
                microservice_name: ServiceMicroserviceConfig(can_restart=True)
                for microservice_name in microservices_in_service
            },
        )
        for service_name, microservices_in_service in level_definition.service_groups
    }

    containers = {
        container_name: ContainerConfig(
            cpu_limit=DEFAULT_CPU_LIMIT,
            services={
                service_name: ContainerServiceConfig(can_restart=True)
                for service_name in service_names
            },
        )
        for container_name, service_names in level_definition.container_groups
    }

    return SimulationConfig(
        request_count=DEFAULT_REQUEST_COUNT,
        log_level=DEFAULT_LOG_LEVEL,
        microservices=microservices,
        services=services,
        containers=containers,
    )


def _build_service_dependencies(
    service_name: str,
    microservices_in_service: tuple[str, ...],
    microservice_dependencies: dict[str, dict[str, DependencyConfig]],
    microservice_to_service: dict[str, str],
) -> dict[str, DependencyConfig]:
    aggregated_dependencies: dict[str, DependencyConfig] = {}

    for microservice_name in microservices_in_service:
        for dependency_name, dependency_config in microservice_dependencies[
            microservice_name
        ].items():
            dependency_service_name = microservice_to_service[dependency_name]
            if dependency_service_name == service_name:
                continue

            existing_dependency = aggregated_dependencies.get(dependency_service_name)
            if existing_dependency is None:
                aggregated_dependencies[dependency_service_name] = DependencyConfig(
                    call_rate=dependency_config.call_rate,
                    stop_on_error=dependency_config.stop_on_error,
                )
                continue

            aggregated_dependencies[dependency_service_name] = DependencyConfig(
                call_rate=max(existing_dependency.call_rate, dependency_config.call_rate),
                stop_on_error=(
                    existing_dependency.stop_on_error or dependency_config.stop_on_error
                ),
            )

    return dict(sorted(aggregated_dependencies.items()))


def _render_level_readme(
    architecture_id: int,
    level_definition: LevelDefinition,
    microservice_dependencies: dict[str, dict[str, DependencyConfig]],
) -> str:
    """Render markdown documentation containing a Mermaid graph for one level."""
    lines = [
        f"# Architecture {architecture_id} - {level_definition.folder_name}",
        "",
        "This folder was generated automatically.",
        "",
        "- Config file: `config.json`",
        "- Graph source: generated microservice dependencies",
        "",
        "```mermaid",
    ]
    lines.extend(_render_mermaid_graph(level_definition, microservice_dependencies))
    lines.extend(["```", ""])
    return "\n".join(lines)


def _render_mermaid_graph(
    level_definition: LevelDefinition,
    microservice_dependencies: dict[str, dict[str, DependencyConfig]],
) -> list[str]:
    """Render Mermaid graph lines with container/service grouping and dependencies."""
    microservice_to_service = {
        microservice_name: service_name
        for service_name, microservices in level_definition.service_groups
        for microservice_name in microservices
    }
    container_to_services: dict[str, tuple[str, ...]] = {
        container_name: service_names
        for container_name, service_names in level_definition.container_groups
    }

    graph_lines: list[str] = ["graph TD"]

    for container_name, service_names in container_to_services.items():
        graph_lines.append(f"    subgraph {container_name} [{container_name}]")
        graph_lines.append("        direction TD")

        for service_name in service_names:
            microservices = tuple(
                name
                for name, mapped_service in microservice_to_service.items()
                if mapped_service == service_name
            )
            graph_lines.append(f"        subgraph {service_name} [{service_name}]")
            graph_lines.append("            direction TD")
            for microservice_name in microservices:
                node_name = _microservice_node_id(microservice_name)
                graph_lines.append(f"            {node_name}[Microservice {microservice_name}]")
            graph_lines.append("        end")

        graph_lines.append("    end")

    graph_lines.append("")
    for source_name in MICROSERVICE_NAMES:
        for target_name in microservice_dependencies[source_name].keys():
            source_node = _microservice_node_id(source_name)
            target_node = _microservice_node_id(target_name)
            graph_lines.append(f"    {source_node} --> {target_node}")

    return graph_lines


def _microservice_node_id(microservice_name: str) -> str:
    """Return a stable Mermaid node id for a microservice name."""
    return f"M{microservice_name}"
