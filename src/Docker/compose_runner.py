"""Docker Compose run and test operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.Docker.platform import DockerPlatform
from src.Common.Utils.logger import get_logger

logger = get_logger(__name__)


def run_docker_compose_file(
    compose_path: str | Path | None = None,
    output_dir: str | Path = ".output",
    detach: bool = True,
) -> None:
    """Run the most recent or explicitly provided Docker Compose file."""
    logger.info(
        "Running Docker Compose configuration: compose_path=%s, output_dir=%s, detach=%s",
        compose_path,
        output_dir,
        detach,
    )
    platform: Any = DockerPlatform()
    platform.run(compose_path=compose_path, output_dir=output_dir, detach=detach)
    logger.info("Docker Compose run completed successfully")


def test_docker_compose_file(
    compose_path: str | Path | None = None,
    output_dir: str | Path = ".output",
    request_count: int | None = None,
) -> dict[str, Any]:
    """Run the generated architecture and collect request/resource metrics."""
    logger.info(
        "Testing Docker Compose configuration: compose_path=%s, output_dir=%s, request_count=%s",
        compose_path,
        output_dir,
        request_count,
    )
    platform: Any = DockerPlatform()
    resolved_compose = _resolve_compose_path(compose_path, output_dir)

    try:
        results = platform.test(
            compose_path=resolved_compose,
            output_dir=output_dir,
            request_count=request_count,
        )
        logger.info("Docker Compose test completed successfully")
        return results
    finally:
        try:
            platform.stop(compose_path=resolved_compose, output_dir=output_dir)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to stop Docker Compose stack after test: %s", exc)


def test_all_docker_configs(
    output_dir: str | Path = ".output",
    request_count: int | None = None,
    missing: bool = False,
) -> list[dict[str, object]]:
    """Build and test every generated config.json under the output directory."""
    output_root = Path(output_dir)
    if not output_root.exists():
        raise RuntimeError(f"Output directory not found: {output_root}")

    config_paths = _discover_generated_config_paths(output_root)
    if not config_paths:
        raise RuntimeError(f"No generated config.json files found under {output_root}")

    logger.info("Testing %d generated Docker configs under %s", len(config_paths), output_root)

    results: list[dict[str, object]] = []
    for config_path in config_paths:
        logger.info("Testing generated config: %s", config_path)
        platform: Any = DockerPlatform()
        compose_path = config_path.parent / "docker-compose.yml"

        # If "missing" is requested and a result CSV already exists for the
        # provided request_count, skip testing this generated config.
        if missing and request_count is not None:
            expected_csv = config_path.parent / f"result_{request_count}.csv"
            if expected_csv.exists():
                logger.info(
                    "Skipping %s for request_count=%s because %s exists",
                    config_path,
                    request_count,
                    expected_csv,
                )
                continue

        try:
            platform.build(str(config_path), str(config_path.parent))
            results.append(
                platform.test(
                    compose_path=compose_path,
                    output_dir=str(config_path.parent),
                    request_count=request_count,
                )
            )
        finally:
            if compose_path.exists():
                try:
                    platform.stop(compose_path=compose_path, output_dir=str(config_path.parent))
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "Failed to stop Docker Compose stack for %s: %s", config_path, exc
                    )

    logger.info("Docker configs test completed successfully: %d runs", len(results))
    return results


def stop_docker_compose_file(
    compose_path: str | Path | None = None,
    output_dir: str | Path = ".output",
) -> None:
    """Stop and remove the generated Docker Compose stack."""
    logger.info(
        "Stopping Docker Compose configuration: compose_path=%s, output_dir=%s",
        compose_path,
        output_dir,
    )
    platform: Any = DockerPlatform()
    platform.stop(compose_path=compose_path, output_dir=output_dir)
    logger.info("Docker Compose stack stopped successfully")


def _discover_generated_config_paths(output_root: Path) -> list[Path]:
    """Return generated config.json files under numeric architecture folders."""
    config_paths: list[Path] = []
    for architecture_dir in sorted(
        child for child in output_root.iterdir() if child.is_dir() and child.name.isdigit()
    ):
        for level_dir in sorted(child for child in architecture_dir.iterdir() if child.is_dir()):
            config_path = level_dir / "config.json"
            if config_path.exists():
                config_paths.append(config_path)

    return config_paths


def _resolve_compose_path(
    compose_path: str | Path | None,
    output_dir: str | Path,
) -> Path:
    """Resolve a docker-compose.yml path using the same rules as the runtime platform."""
    if compose_path is not None:
        resolved = Path(compose_path)
        if resolved.is_dir():
            resolved = resolved / "docker-compose.yml"
        if not resolved.exists():
            raise RuntimeError(f"Compose file not found: {resolved}")
        return resolved.resolve()

    search_root = Path(output_dir)
    if not search_root.exists():
        raise RuntimeError(f"Output directory not found: {search_root}")

    direct_compose = search_root / "docker-compose.yml"
    if direct_compose.exists():
        return direct_compose.resolve()

    candidates = sorted(
        search_root.glob("*/docker-compose.yml"), key=lambda path: path.stat().st_mtime
    )
    if not candidates:
        raise RuntimeError(f"No docker-compose.yml found under {search_root}")
    return candidates[-1].resolve()
