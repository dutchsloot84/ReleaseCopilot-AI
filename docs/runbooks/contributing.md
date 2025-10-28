# Contributing Runbook (Wave 3)

The Wave 3 Mission Outline Plan codified our contributor workflow, including the adoption of shared pre-commit hooks.

## Install tooling

1. Create or update your development environment:
   ```bash
   pip install -e .[dev]
   ```
2. Install the hooks locally:
   ```bash
   pre-commit install
   ```
3. Run every hook at least once before opening a pull request. CI runs the same entrypoint but supplements it with heavier checks downstream; keep timestamps in America/Phoenix (UTC-7 year round):
   ```bash
   pre-commit run --all-files --show-diff-on-failure
   ```

## What the hooks enforce

- `ruff check --fix` applies lint fixes and flags style regressions.
- `ruff format` keeps Python code deterministic without relying on Black.
- `codespell` guards against spelling regressions in text assets.

The `.github/workflows/ci.yml` pipeline builds on these quick hooks by running `pip install -e .[dev]`, mypy, generator drift detection, prompt validation, and the pytest + coverage gate on Python 3.11.x before packaging/CDK jobs begin. Any failure blocks packaging and deployment jobs downstream.

### Test isolation policies

- `tests/conftest.py` provides the global `config.settings` stub and enforces the Phoenix timezone plus `ENABLE_NETWORK = False`.
- Socket creation is blocked session-wide; live HTTP calls should raise immediately.
- Tests must not edit `sys.path` or mutate `sys.modules`; prefer `importlib.reload` and monkeypatching of imported symbols.

## Troubleshooting

- **Hook updates** — When dependencies change, bump the versions in `.pre-commit-config.yaml` to match the pinned versions declared in `pyproject.toml` and re-run `pre-commit autoupdate` locally before committing the diff.
- **Phoenix timestamps missing** — If hook output shows another timezone, export `TZ=America/Phoenix` when running hooks and update your shell profile so logs match automation expectations.
- **Bypassing hooks** — Avoid using `SKIP=` unless the Mission Outline Plan explicitly instructs otherwise. CI enforces the hooks, so local bypasses will fail the pipeline.
