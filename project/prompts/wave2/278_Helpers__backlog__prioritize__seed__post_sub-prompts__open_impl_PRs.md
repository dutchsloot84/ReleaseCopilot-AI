# Wave 2 – Sub-Prompt · [278] Helpers: backlog, prioritize, seed, post sub-prompts, open impl PRs

**Context:** Use the active MOP; honor constraints & quality bar (Phoenix TZ: America/Phoenix).

**Acceptance Criteria (copy into PR):**
- Implement: Helpers: backlog, prioritize, seed, post sub-prompts, open impl PRs (#278)
- Tests (no live network), ≥70% coverage on touched code; docs + CHANGELOG.
- PR markers: Decision / Note / Action.
- Phoenix TZ noted where schedulers/cron/log timestamps apply.

## Implementation Targets
- Build a helper automation module at `scripts/github/wave2_helper.py` with subcommands:
  - `collect` – wraps `gh issue list` but accepts `--issues-json` for offline tests; filters labels (`wave:wave2`, `mop`, `automation`, `ci`, `github-integration`).
  - `prioritize` – scores issues using label weights (high-priority > automation > ci > github-integration) and outputs deterministic `artifacts/helpers/prioritized-issues.json` with Phoenix timestamps in metadata.
  - `seed` – hydrates prompt templates under `project/prompts/wave2/` by merging issue metadata and MOP constraints.
  - `post` – prepares Markdown comment bodies (stored locally under `artifacts/helpers/comments/ISSUE.md`) for manual posting; include placeholders for Phoenix scheduling notes.
  - `open-pr` – scaffolds a branch and PR body template in `artifacts/helpers/pr_template.md` without pushing.
- Introduce a reusable configuration file `config/wave2_helper.yml` describing label weights, maintainers, and artifact directories.
- Ensure helper scripts rely on environment variables for tokens (e.g., `GITHUB_TOKEN`), but avoid network calls in tests by injecting mock adapters.
- Provide CLI entry point via `python -m scripts.github.wave2_helper` and document usage.

## Testing Expectations
- Add unit tests in `tests/github/test_wave2_helper.py` covering:
  - Deterministic prioritization (stable ordering with same inputs).
  - Artifact emission with Phoenix timezone metadata.
  - Seeded prompt interpolation using fixture issues.
- Add integration-style test in `tests/ops/test_helper_cli.py` using `CliRunner` or `subprocess` to execute `--issues-json` path.
- Verify coverage for new modules remains ≥70%; add factories in `tests/fixtures/issues_wave2.json` for reuse.

## Documentation & Runbooks
- Write `docs/promptops/helpers.md` capturing helper commands, artifact paths, and Phoenix timezone rationale.
- Update `docs/promptops/MOP_Workflow.md` to mention the helper automation pipeline.
- Add CHANGELOG entry referencing helper tooling and deterministic artifacts.

## Rollback & Observability
- Emit audit trail entries in `artifacts/helpers/activity-log.ndjson`; include command name, Phoenix timestamp, and deterministic UUID.
- Provide rollback section in docs: delete generated artifacts and remove CLI entrypoint from `scripts/github/__init__.py` if necessary.
- Add logging via `releasecopilot.logging_config` to centralize helper logs; ensure tests assert that secrets are redacted.

**Critic Check:**
- Lint/format/mypy pass? Coverage ≥ gate?
- No secrets logged; least-priv IAM?
- Phoenix cron/DST stated?
- Artifacts deterministic with run metadata?
