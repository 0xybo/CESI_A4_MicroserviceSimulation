---
description: 'Use when editing Docker runtime generation, compose lifecycle, runtime runner HTTP flow, output artifacts, or container test/stop commands in src/Docker.'
name: 'Docker Runtime Rules'
applyTo: 'src/Docker/**/*.py'
---

# Docker Runtime Rules

## Scope

- Apply these rules to compose generation, runtime startup, test execution, and stop/cleanup logic in src/Docker.
- Keep compatibility with the unified CLI in src/**main**.py and direct Docker CLI in src/Docker/**main**.py.

## Behavioral Guardrails

- Preserve generated artifact shape under .output timestamp folders.
- Keep compose discovery behavior stable when compose path is omitted.
- Ensure test command can still resolve request count from config when --requests is not supplied.
- Maintain stop behavior so stacks are removable without manual cleanup steps.

## Runtime Runner And Endpoint Safety

- Keep runtime runner endpoint contracts backward compatible for generated clients.
- Preserve per-request duration and per-container resource usage reporting fields.
- Avoid changing default paths/names for generated config and result files unless task explicitly requires it.

## Logging And Diagnostics

- Continue redirecting container stdout/stderr to runtime output logs.
- Keep error messages actionable and include affected compose/config path when possible.

## Validation Checklist

1. Build: python -m src build --config config-test.json --output .output
2. Run: python -m src run --output .output
3. Test: python -m src test --output .output --requests 5
4. Stop: python -m src stop --output .output
5. Confirm expected artifacts exist in the newest .output run folder.

## References

- DOCKER_USAGE.md
- src/**main**.py
- src/Docker/**main**.py
- src/Docker/build.py
- src/Docker/runtime_runner.py
