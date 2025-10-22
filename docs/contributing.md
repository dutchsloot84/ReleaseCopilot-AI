# Contributor Workflow (Lint, Format, Type Check)

**Decision:** Use Ruff for linting and formatting with mypy and pytest gates mirrored locally and in CI.
**Note:** Runbook timestamps and automation guidance follow America/Phoenix (no DST) per the Release Copilot MOP.
**Action:** Install pre-commit, run `ruff format .`, `ruff check --fix .`, and `mypy`/`pytest` locally before pushing.

## Local checklist

1. `pip install -e .[dev]`
2. `pre-commit install`
3. `ruff check --fix .`
4. `ruff format .`
5. `pre-commit run --all-files`
6. `mypy -p releasecopilot -p src.cli -p clients`
7. `pytest`

## CI mirrors

GitHub Actions executes `pre-commit run --all-files --show-diff-on-failure`, followed by `ruff check .`, `ruff format --check .`, `mypy -p releasecopilot -p src.cli -p clients`, and `pytest` with the 70% coverage gate. Failures must be resolved locally before merging.
