# Contributing

Thank you for investing in Release Copilot! This guide captures contributor expectations that do not fit elsewhere in the docs set.

## License and contribution terms

Release Copilot is released under the [MIT License](LICENSE). By submitting a pull request, you agree that your contribution will be licensed under the same terms. We do not require a contributor license agreement or Developer Certificate of Origin sign-off.

## Notes & decision markers

Release Copilot ingests structured markers from issues and pull requests (Decision, Note, Action, Blocker) when building the weekly history snapshots. To keep the noise level low and make PR review threads easy to scan, prefer **block style markers** when you have multiple follow-up items to record:

```markdown
Decision:
- Canonicalize CDK config to infra/cdk/cdk.json.
- Treat any additional cdk.json outside infra/cdk/cdk.json as unsupported for CI.

Action:
- Add guardrail script to fail the build if non-canonical cdk.json files are committed.
```

Block style keeps every bullet tied to a single marker heading so reviewers do not have to parse repeated prefixes, while Git Historian still captures each bullet individually.

Inline markers are still supported and are handy for short, one-off notes:

```markdown
Note: Retry `cdk list` with `--verbose` if the default invocation flakes.
```

> **Tip:** Inline style is great for scratch notes or quick comments, but block style is the preferred format for PR reviews, RFC feedback, and any thread where you are communicating multiple decisions or follow-up items.

## Import hygiene skill (quick start)

Decision:
- Keep ruff/isort as the source of truth for organizing imports across all Python modules.

Note (2025-02-14 America/Phoenix):
- [pre-commit.ci](https://pre-commit.ci/) runs on every pull request and may push a `chore(pre-commit): auto fixes from pre-commit.ci` commit when lint finds reorderings.
- The project enforces a single `src` package root. Imports should never be prefixed with `src.`; rely on the package names (`cli`, `export`, `releasecopilot`, etc.) instead.

Action:
- Run `pre-commit install` once so the ruff hooks execute locally before each commit.

Follow these steps whenever you touch imports:

1. Format and sort locally with `ruff check --fix .` followed by `ruff format .`.
2. Run `pre-commit run --all-files` to confirm there are no lingering lint adjustments.
3. If CI still reports import changes, wait for pre-commit.ci to push its fix commit or run the hooks locally and push again.

Troubleshooting tips:

- If ruff raises module grouping errors (I001), ensure the module belongs to one of the configured sections: stdlib, third-party, `config`/`releasecopilot`, then relative imports.
- When a PR originates from a fork, pre-commit.ci cannot push auto-fix commits. In that situation the workflow fails with a reminder—run the commands above locally and push manually.
- Verify `python -m pip install -r requirements-dev.txt` so the local hooks share the same versions as CI.

## Linting & pre-commit.ci

- Local: `pre-commit run --all-files` applies ruff fixes, formatting, mypy, and ancillary checks before you push.
- Pull requests: [pre-commit.ci](https://pre-commit.ci/) runs the same hooks, may push auto-fix commits, and reruns its checks after applying fixes.
- GitHub Actions installs the repository in editable mode, then runs check-only linting via `scripts/ci/run_precommit.sh` (`ruff format --check .`, `ruff check --output-format=github .`, and `mypy --config-file pyproject.toml`); Actions never applies auto-fixes.
- The `check-generated-wave` hook calls `python -m tools.hooks.check_generator_drift` to regenerate Wave artifacts and asserts `docs/mop`, `docs/sub-prompts`, and `artifacts/` match Git history.
- Set `RELEASECOPILOT_SKIP_GENERATOR=1` when you intentionally skip regeneration (for example, on CI jobs that stage artifacts beforehand).
- On failure it exits with drift instructions so you can re-run `python -m releasecopilot.cli_releasecopilot generate --spec backlog/wave3.yaml --timezone America/Phoenix --archive` and commit the refreshed outputs.

## Tests & coverage

Pytest defaults to `--cov=src` and writes JSON/XML reports so CI can enforce the ≥70% threshold from `pyproject.toml`.
Infrastructure helpers in `infra/`, `scripts/`, and `tools/` plus entry-point wrappers like `src/**/__main__.py` are omitted from coverage calculations, keeping the gate focused on application code.

## CLI entry points

- Implement new CLIs as modules under `src/<package>/cli_<topic>.py` with a `main(argv: list[str] | None = None) -> int` signature and `if __name__ == "__main__": raise SystemExit(main())` guard.
- Register the console script in `[project.scripts]` within `pyproject.toml` so editable installs expose the entry point (for example `releasecopilot = "releasecopilot.cli_releasecopilot:main"`).
- Tests that shell out to the CLI should pass `PYTHONPATH=src:.` (or rely on the installed console script) rather than editing `sys.path` inside the implementation.
