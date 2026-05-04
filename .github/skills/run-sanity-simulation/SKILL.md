---
name: run-sanity-simulation
description: 'Run a quick end-to-end sanity simulation for this repository. Use for smoke checks after code changes in runtime, config, monitoring, or CLI behavior.'
argument-hint: 'Optional mode: python-only, docker-only, or full'
---

# Run Sanity Simulation

Use this skill to verify that core simulation paths still work after changes.

## When To Use

- After editing src/Python or src/Common execution behavior.
- After editing src/Docker generation, runner, or lifecycle commands.
- After changing config models, aliases, or CLI command parsing.

## Inputs

- Optional argument values:
    - python-only
    - docker-only
    - full (default)

## Procedure

1. Activate the repository's Python environment (`.venv/`) if needed.
    - For example, `source .venv/bin/activate` on Unix or `.venv\Scripts\activate` on Windows.
2. Install dependencies if needed:
    - pip install -r requirements.txt
3. If argument is docker-only or full, run Docker lifecycle:
    - python -m src build --config config-test.json --output .output
    - python -m src run --output .output
    - python -m src test --output .output --requests 5
    - python -m src stop --output .output
4. Validate expected outputs:
    - .logs contains runtime logs
    - newest .output run folder contains generated artifacts and result data
5. Report:
    - commands executed
    - pass/fail per step
    - first actionable error if any step fails

## Notes

- Do not modify generated artifacts manually unless the task is specifically about artifact generation.

## References

- README.md
- DOCKER_USAGE.md
- config-test.json
