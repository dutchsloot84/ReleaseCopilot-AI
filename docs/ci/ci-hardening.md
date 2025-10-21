# CI Hardening Report

## Overview

We restructured the GitHub Actions pipeline to make linting, type-checking, and
tests resilient across Python 3.10 and 3.11 while enforcing the same
pre-commit, mypy, and pytest gates developers use locally. The workflow now runs
as three independent jobs (`lint`, `typecheck`, and `tests`) that fan out across
a Python matrix, enabling faster feedback and better failure isolation before
packaging or CDK synthesis begin.

## Workflow Layout

- **Lint job:** Executes `pre-commit run --all-files` (ruff, ruff-format, mypy,
  codespell, YAML/whitespace checks) on Python 3.10 and 3.11 with cached
  virtualenvs. The optional Ruff autofix trigger for `workflow_dispatch` remains
  available for import hygiene cleanups.
- **Type check job:** Runs mypy (packages `releasecopilot`, `cli`, and
  `clients`) with a reusable cache, leveraging the stricter settings consolidated
  in `pyproject.toml`.
- **Test job:** Executes pytest with coverage and the 70% gate on Python 3.10
  and 3.11. Only the Python 3.11 leg posts the PR coverage summary and uploads
  coverage artifacts. Downstream jobs (`package`, `cdk-synth`) require the
  matrix to succeed.

## Tooling Configuration

- Ruff, Ruff-format, mypy, pytest, and black share a single source of truth in
  `pyproject.toml`. The mypy settings enable strict equality, disallow untyped
  definitions, and fall back to targeted overrides (`services.*`, `rag_aws.*`)
  while preserving stub usage (`types-requests`, `types-PyYAML`).
- The pytest configuration enforces deterministic coverage reports (term,
  JSON, XML), `-ra` summaries, Phoenix time zone expectations, and strict
  markers. The autouse fixtures continue to disable real network access.
- The pre-commit configuration adds codespell, YAML formatting, trailing
  whitespace, and EOF hooks so CI and local development run the same toolchain.

## Caching Strategy

- `actions/cache@v4` now covers pip wheels, the pre-commit cache, mypy cache,
  and `.pytest_cache`, drastically shrinking warm-run durations.
- Cache keys incorporate the runner OS, Python version, and
  `pyproject.toml`/requirements hashes to avoid stale environments while
  keeping hot caches between PRs.

## Coverage Gate & Reporting

- Pytest produces `coverage.json` and `coverage.xml` on every matrix leg.
- `tools/coverage_gate.py` enforces ≥70% coverage overall or on the touched
  files subset when available.
- The Python 3.11 test leg posts a PR coverage summary comment and uploads the
  reports as an artifact for manual inspection.

## Phoenix Timestamp & Network Policy

- The shared pytest fixtures pin `config.settings.DEFAULT_TIMEZONE` to
  `America/Phoenix` and forbid socket creation, satisfying the project’s
  Phoenix timestamp and “no live network” directives.
- Tests that legitimately require network access must opt in via the
  `@pytest.mark.network` marker and be quarantined or justified separately.

## Troubleshooting & Remediation

1. **Lint failures:** Re-run `pre-commit run --all-files`. Ruff findings can be
   autofixed locally via `ruff check --fix . && ruff format .`.
2. **Type errors:** Install dev dependencies and run `mypy -p releasecopilot -p
   cli -p clients`. Add targeted ignores only with justification in
   `pyproject.toml`.
3. **Coverage failures:** Run `pytest` locally; re-gate with
   `python tools/coverage_gate.py coverage.json --minimum 70 --paths "$(git diff --name-only origin/main...HEAD -- '*.py')"`.
4. **Cache corruption:** Drop the relevant caches from the Actions UI or bump
   `pyproject.toml`/requirements hashes.

## Rollback Plan

If the hardened pipeline causes disruption, revert the changes to
`.github/workflows/ci.yml`, `.pre-commit-config.yaml`, and `pyproject.toml` while
retaining this document for historical context. The previous single-job
`python-checks` workflow can be restored from git history, and the deleted
`mypy.ini` / `pytest.ini` may be recovered if needed.

## Local Re-run Recipe

```bash
python -m pip install -r requirements-dev.txt
pre-commit run --all-files
mypy -p releasecopilot -p cli -p clients
pytest
python tools/coverage_gate.py coverage.json --minimum 70
```
