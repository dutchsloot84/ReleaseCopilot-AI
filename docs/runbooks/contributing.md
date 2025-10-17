# Contributing Runbook (Wave 3)

The Wave 3 Mission Outline Plan codified our contributor workflow, including the adoption of shared pre-commit hooks.

## Install tooling

1. Create or update your development environment:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```
2. Install the hooks locally:
   ```bash
   pre-commit install
   ```
3. Run every hook at least once before opening a pull request. CI runs the same command and expects timestamps in America/Phoenix (UTC-7 year round):
   ```bash
   pre-commit run --all-files --show-diff-on-failure
   ```

## What the hooks enforce

- `ruff --fix` applies lint fixes and flags style regressions.
- `black` formats Python code deterministically.
- `mypy` performs static type checks using the repository configuration.

The `.github/workflows/ci.yml` pipeline executes `scripts/ci/run_precommit.sh` ahead of tests. A failure here blocks packaging and deployment jobs downstream.

## Troubleshooting

- **Hook updates** — When dependencies change, bump the versions in `.pre-commit-config.yaml` to match `requirements-dev.txt` pins and re-run `pre-commit autoupdate` locally before committing the diff.
- **Phoenix timestamps missing** — If hook output shows another timezone, export `TZ=America/Phoenix` when running hooks and update your shell profile so logs match automation expectations.
- **Bypassing hooks** — Avoid using `SKIP=` unless the Mission Outline Plan explicitly instructs otherwise. CI enforces the hooks, so local bypasses will fail the pipeline.
