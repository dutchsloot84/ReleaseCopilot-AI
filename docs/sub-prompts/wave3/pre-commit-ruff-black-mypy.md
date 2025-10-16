# Wave 3 – Sub-Prompt · [AUTO] [Pre-commit] ruff, black, mypy

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- .pre-commit-config.yaml lands; README has install steps.
- pre-commit run --all-files passes in CI.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Add `.pre-commit-config.yaml` at repo root configuring `ruff`, `black`, and `mypy` hooks pinned to existing versions from `requirements-dev.txt`.
- Update `requirements-dev.txt` to include `pre-commit` if absent (no other dependency changes).
- Modify CI script (e.g., `scripts/ci/run_precommit.sh`) to execute `pre-commit run --all-files` prior to pytest and ensure gating.
- Document installation and usage in `README.md` and `docs/runbooks/contributing.md`, mentioning Phoenix timezone expectations for logs if hooks emit timestamps.
- Sequence: add config → ensure dev requirements include pre-commit → update CI script → document setup/tests.

### Key code snippets
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: ["--fix"]
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: ["types-requests"]
```

```bash
# scripts/ci/run_precommit.sh
#!/usr/bin/env bash
set -euo pipefail
pre-commit run --all-files --show-diff-on-failure
```

### Tests (pytest; no live network)
- Not applicable for runtime, but run `pre-commit run --all-files` locally to ensure hooks succeed.
- Add automation in CI to fail when hooks fail; optionally add `tests/ci/test_precommit_config.py::test_config_loads` to ensure YAML schema validity.

### Docs excerpt (README/runbook)
Add to `README.md` development setup:

> Install pre-commit hooks via `pip install -r requirements-dev.txt` followed by `pre-commit install`. Run `pre-commit run --all-files` before pushing to mirror CI. Hooks use America/Phoenix timestamps when logging durations.

Update `docs/runbooks/contributing.md`:

> Pre-commit enforces `ruff`, `black`, and `mypy` across Python sources. CI executes `pre-commit run --all-files` ahead of pytest; failures must be resolved locally.

### Risk & rollback
- Risks: version pin conflicts with existing formatting tools; CI time increase; hooks misconfigured for Windows paths.
- Rollback: remove `.pre-commit-config.yaml`, revert CI script, and prune documentation references.
- No data migrations; dependencies limited to dev tooling.


## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Run `pre-commit run --all-files` after configuration; ensure hooks do not log secrets.
- Verify CI includes the pre-commit step with gating.
- Keep versions aligned with `requirements-dev.txt` pins.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Adopt pre-commit hooks for ruff, black, and mypy.
- **Note:** Developers must install hooks via requirements-dev instructions.
- **Action:** Add pre-commit config, update CI invocation, and document setup.
