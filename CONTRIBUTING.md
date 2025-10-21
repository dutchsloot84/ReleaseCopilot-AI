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
- CI will auto-fix import ordering on pull requests and push a `[skip ci]` commit titled `style: organize imports (ruff isort)` if required.

Action:
- Run `pre-commit install` once so the ruff hooks execute locally before each commit.

Follow these steps whenever you touch imports:

1. Format and sort locally with `ruff check --fix .` followed by `ruff format .`.
2. Run `pre-commit run --all-files` to confirm there are no lingering lint adjustments.
3. If CI still reports import changes, fetch the bot's auto-fix commit, rebase, and push again.

Troubleshooting tips:

- If ruff raises module grouping errors (I001), ensure the module belongs to one of the configured sections: stdlib, third-party, `config`/`releasecopilot`, then relative imports.
- When a PR originates from a fork, GitHub Actions cannot push auto-fix commits. In that situation the workflow fails with a reminder—run the commands above locally and push manually.
- Verify `python -m pip install -r requirements-dev.txt` so the local hooks share the same versions as CI.
