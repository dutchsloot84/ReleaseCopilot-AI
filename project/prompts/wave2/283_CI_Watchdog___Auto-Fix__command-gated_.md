# Wave 2 – Sub-Prompt · [283] CI Watchdog + Auto-Fix (command-gated)

**Context:** Use the active MOP; honor constraints & quality bar (Phoenix TZ: America/Phoenix).

**Acceptance Criteria (copy into PR):**
- Implement: CI Watchdog + Auto-Fix (command-gated) (#283)
- Tests (no live network), ≥70% coverage on touched code; docs + CHANGELOG.
- PR markers: Decision / Note / Action.
- Phoenix TZ noted where schedulers/cron/log timestamps apply.

## Implementation Targets
- Create `.github/workflows/ci-watchdog.yml`:
  - Scheduled run at 14:00 UTC daily (07:00 America/Phoenix, no DST); add `workflow_dispatch` for manual triggering and `/watchdog autofix` slash command support.
  - Jobs: `scan` (collect failing checks via GitHub REST), `report` (comment summary), `autofix` (runs only when command-gated and approvals present).
  - Use `ORCHESTRATOR_BOT_TOKEN` with least-priv scopes (`checks:read`, `pull_requests:write`); never echo secrets.
  - Persist findings to `artifacts/watchdog/<phoenix-date>/status.json` and append NDJSON to `artifacts/watchdog/activity-log.ndjson`.
- Implement helper script `scripts/github/ci_watchdog.py` with functions:
  - `collect_failures(repo: str, max_age_hours: int)` returning deterministic data structures (sorted by PR number).
  - `render_report(failures)` generating Markdown tables (without secrets) and Phoenix timestamp headers.
  - `should_autofix(event)` verifying the command source, labels (`automation`), and gating approvals.
- Add `scripts/github/run_watchdog_autofix.sh` orchestrating lint/format commands (`ruff check --fix`, `black`, targeted `pytest`) for flagged PRs; ensure no network access.

## Testing Expectations
- Unit tests under `tests/github/test_ci_watchdog.py` mocking GitHub responses (use fixture JSON under `tests/fixtures/github/watchdog/`). Cover: no failures, stale failures, autofix gating.
- Add CLI integration test `tests/ops/test_ci_watchdog_cli.py` to simulate scheduled invocation with Phoenix timezone set.
- Provide golden snapshot for rendered Markdown in `tests/golden/watchdog/report.md`; assert deterministic ordering and timestamp format.

## Documentation & Runbooks
- Update `docs/CI_CD/ci-watchdog.md` with workflow overview, Phoenix schedule (07:00 local), and gating instructions.
- Document autofix safeguards in `docs/promptops/helpers.md` or a new `docs/promptops/watchdog.md`.
- Add CHANGELOG entry summarizing watchdog automation and command gating.

## Rollback & Observability
- Publish job summaries via `actions/github-script` to the workflow summary; include sanitized Phoenix timestamps and counts.
- Provide rollback plan: disable workflow scheduling, revert `.github/workflows/ci-watchdog.yml`, and purge `artifacts/watchdog/` if necessary.
- Emit metrics-friendly counters in `artifacts/watchdog/metrics.json` (failures scanned, autofixes attempted) for manual review.

**Critic Check:**
- Lint/format/mypy pass? Coverage ≥ gate?
- No secrets logged; least-priv IAM?
- Phoenix cron/DST stated?
- Artifacts deterministic with run metadata?
