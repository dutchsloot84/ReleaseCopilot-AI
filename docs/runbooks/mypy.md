# mypy Execution

**Decision:** Keep `mypy --config-file pyproject.toml` as the single source of truth for type checks across CI and local runs.
**Note:** Prefer tightening ignores incrementally—document any temporary `type: ignore` annotations in PR descriptions.
**Action:** Install dev extras, invoke mypy via `pre-commit` or CLI, and refresh stubs when third-party packages bleed `Any`.

## Installation

```bash
python -m pip install --upgrade pip wheel
pip install -e .[dev]
```

This mirrors the CI lint job, ensuring `types-requests`, `types-PyYAML`, and local hooks resolve identically.

## Running mypy

- Primary command: `mypy --config-file pyproject.toml` (same as CI matrix).
- Scoped package checks: `mypy -p releasecopilot -p clients -p services` when iterating quickly.
- Pre-commit integration: `python -m pre_commit run mypy --all-files` shares caches with CI via `~/.cache/pre-commit`.

## Fixing failures

1. Read errors from Phoenix-stamped output (timezone is fixed via `ZoneInfo("America/Phoenix")`).
2. If a dependency lacks stubs, add the pinned package under `[tool.mypy].extra_dependencies` or include `.pyi` files beside sources.
3. Avoid `ignore_errors`; prefer targeted `# type: ignore[code]` annotations with comments.
4. When touching prompts or generators, set `PHOENIX_TIMESTAMP_OVERRIDE` to an ISO-8601 Phoenix time to keep regenerated manifests deterministic before rerunning mypy.

## Troubleshooting

- Delete `.mypy_cache` or run `pre-commit clean` if stubs change upstream.
- Ensure `PYTHONPATH` points at the repo root when running scripts directly: `export PYTHONPATH=$(pwd)`.
- Cross-check Poetry/venv activation—CI installs via `pip install -e .[dev]`, so match that environment locally.
