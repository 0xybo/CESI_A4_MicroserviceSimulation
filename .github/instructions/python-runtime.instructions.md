---
description: 'Use when editing Python runtime execution, microservice orchestration, request flow, execution metrics, or thread-based simulation behavior in src/Python and src/Common.'
name: 'Python Runtime Rules'
applyTo: 'src/Common/**/*.py'
---

# Python Runtime Rules

## Scope

- Apply these rules when changing execution logic in src/Python or shared domain logic in src/Common.
- Keep changes local to the runtime concern requested by the task.

## Behavioral Guardrails

- Preserve the execution chain: Microservice -> Service -> Container.
- Preserve ExecutionContext propagation through service and microservice calls.
- Do not rename or remove metrics keys without updating all readers/writers that consume them.
- Keep request count and worker validations intact or stricter, never weaker.

## Concurrency And Determinism

- Threading behavior must remain explicit and easy to reason about.
- Avoid introducing hidden global mutable state in execution paths.
- Keep failure simulation semantics stable for error_rate, work_difficulty, and delay fields.

## Logging And Errors

- Use existing logger utilities from src/Common/Utils/logger.py.
- Log structured, actionable messages on runtime failures.
- Prefer raising explicit errors for invalid runtime arguments.

## Validation Checklist

1. Run: python -m src.Python.main --config config-test.json --requests 10 --workers 1
2. If touched parallel behavior, also run: python -m src.Python.main --config config-test.json --requests 10 --workers 2
3. Confirm logs are produced under .logs and output remains valid JSON when --output is used.
4. Confirm no regression in metrics presence for executed microservices.

## References

- README.md
- src/Python/main.py
- src/Python/platform.py
- src/Common/Microservice/context.py
- src/Common/Microservice/metrics.py
