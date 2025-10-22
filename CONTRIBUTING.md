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
- Verify `pip install -e .[dev]` so the local hooks share the same versions as CI and expose the console entry points used by automation.

## Entry points and coverage policy

- Console scripts are defined in `pyproject.toml` under `[project.scripts]`. New
  executables should live under `src/releasecopilot/entrypoints/` (or an adjacent
  src package) and expose a `main(argv: Sequence[str] | None = None) -> int` function.
  Add the script to `[project.scripts]` and include tests that exercise the module
  via `python -m <package.module>` so imports remain src-aware.
- Prefer running tooling through console scripts (`rc`, `rc-audit`, `rc-recover`,
  `rc-wave2`) or `python -m releasecopilot.entrypoints.<name>` in CI and tests; direct
  invocation of legacy wrappers (for example `main.py`) is deprecated.
- Coverage gates are configured in `pyproject.toml` with `source = ["src", "clients",
  "config", "exporters", "processors", "services", "matcher", "ops", "ui"]` and omit
  infra/tooling paths. Keep additional runtime packages in that list so the
  `tools/coverage_gate.py` check and PR coverage comment remain stable at the 70%
  threshold.
- pre-commit.ci auto-applies lint fixes on pull requests; if a hook fails in CI,
  run `pre-commit run --all-files` locally or wait for the bot’s follow-up commit.
