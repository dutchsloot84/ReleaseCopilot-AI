# CI Hardening Playbook

## Matrixed Workflow Overview
- Split the main pipeline into matrixed jobs for Python versions and operating systems so coverage, lint, and type gates run in parallel.
- Share reusable job definitions via workflow call/`uses` blocks to keep schedules and secrets consistent across triggers.
- Ensure release and pull request workflows both reference the hardened pipeline to avoid drift between branches.

## Tooling Standardization
- Ruff handles linting (`ruff check`) and formatting (`ruff format --check`) in every job.
- Mypy runs with the shared `mypy.ini` configuration to enforce typing gates consistently.
- Pytest executes with `--cov=src` and writes coverage XML for the coverage gate.
- Pre-commit mirrors these commands locally so contributors have the same toolchain as CI.

## Caching Wins
- Python dependencies install from the Poetry/pip cache keyed by `pyproject.toml`, `poetry.lock`, and Python version.
- Ruff, mypy, and pytest reuse cache directories persisted between runs to reduce cold starts.
- Coverage artifacts upload once per matrix entry and reuse shared storage for summary aggregation.

## Coverage Gate Enforcement
- `scripts/ci/coverage_gate.py` compares coverage XML against the required threshold and fails the job if coverage drops.
- The coverage gate runs after pytest in each matrix entry and posts a summary artifact for reviewers.
- Contributors must refresh golden coverage data when adding or removing modules to avoid gate regressions.

## Phoenix Timestamp Policy
- All timestamps emitted by CI use the America/Phoenix timezone (UTC−07:00, no DST).
- Workflow cron schedules and generated artifacts (logs, manifests, archives) must be stamped with Phoenix time.
- Contributors should verify local overrides with `TZ="America/Phoenix"` when reproducing CI results.

## Rollback Instructions
1. Disable the hardened workflow by toggling `workflow_dispatch` and scheduled triggers in `.github/workflows/ci.yml`.
2. Revert to the last known good workflow commit using `git revert` or by restoring from the release tag.
3. Clear caches in the GitHub Actions UI to remove stale dependencies or coverage data.
4. Re-run the baseline CI workflow to confirm the rollback and communicate the status in the Phoenix-time incident log.
