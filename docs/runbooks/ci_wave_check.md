# Wave Artifact Drift Check Runbook

## Purpose
The `check-generated-wave` pre-commit hook and CI step ensure the committed Mission Outline Plan,
sub-prompts, and issue artifacts generated from `backlog/wave3.yaml` remain in sync with the
source specification. The guard executes `python scripts/check_generated_wave.py --mode=check`,
regenerates artifacts in a temporary directory, and compares them byte-for-byte against the
repository contents.

## When the check fails
1. Review the failure message for the list of stale or missing artifacts.
2. Run `make gen-wave` locally to regenerate outputs with Phoenix timestamps.
3. Inspect the diffs under `docs/mop/`, `docs/sub-prompts/`, `artifacts/issues/`, and
   `artifacts/manifests/`.
4. Commit the refreshed artifacts and re-run the hook or CI job.

## Determinism requirements
- Always execute the generator with `--timezone America/Phoenix`; avoid local timezone leakage.
- Do not edit generated artifacts manually. Instead, update `backlog/wave3.yaml` and rerun the
  generator.
- The checker copies `templates/` into an isolated directory, reuses the manifest timestamp when
  available, and enforces byte-for-byte equality. Any nondeterminism (e.g., timestamps, ordering)
  must be addressed in the generator before committing new artifacts.

## Local workflow
1. Install dependencies with `pip install -r requirements-dev.txt` (or use the project Poetry
   environment if preferred).
2. Run `pre-commit run --all-files` to execute the same hook suite as CI.
3. Use `python scripts/check_generated_wave.py --mode=check` to validate artifact freshness without
   mutating the repository.
4. Regenerate artifacts with `make gen-wave` when the check reports drift, then commit the updates.

## Additional resources
- [`docs/runbooks/generator.md`](generator.md) – detailed generator usage and troubleshooting.
- [`README.md`](../../README.md#generating-waves-yaml--mopsub-promptsissues) – contributor quickstart
  for Wave generation.
