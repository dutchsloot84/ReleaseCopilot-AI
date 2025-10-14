# Wave 2 – Sub-Prompt · [277] Add Orchestrator workflow (slash-commands + dispatch)

**Context:** Use the active MOP; honor constraints & quality bar (Phoenix TZ: America/Phoenix).

**Acceptance Criteria (copy into PR):**
- Implement: Add Orchestrator workflow (slash-commands + dispatch) (#277)
- Tests (no live network), ≥70% coverage on touched code; docs + CHANGELOG.
- PR markers: Decision / Note / Action.
- Phoenix TZ noted where schedulers/cron/log timestamps apply.

## Implementation Targets
- Provision `.github/workflows/orchestrator-runner.yml`:
  - Trigger on `workflow_dispatch` and `issue_comment` events filtered for `/orchestrate`.
  - Normalize all timestamps with `TZ: America/Phoenix` for job steps and emitted artifacts.
  - Steps: checkout → setup Python (pinned version) → install project via `pip install -e .[dev]` → run `rc orchestrator dispatch --event-path $GITHUB_EVENT_PATH` → upload `artifacts/orchestrator/*` via `actions/upload-artifact`.
  - Gate execution to comments authored by members of `releasecopilot-maintainers` or those with `triage` permissions by calling a reusable script.
- Add `scripts/github/check_comment_permissions.py` (no network in unit tests) that reads the GH event JSON, validates membership via provided environment variables (e.g., `ALLOWED_ROLES`), and exits non-zero otherwise. Document how production uses a pre-populated list or REST stub; do not hit live GitHub during tests.
- Define a reusable workflow `.github/workflows/reusable-orchestrator.yml` triggered by `workflow_call` so helpers can dispatch without duplicating logic.
- Store the GitHub REST token name as `ORCHESTRATOR_BOT_TOKEN`; the workflow must never echo it. Use least-privilege PAT scopes (`issues:read`, `workflows:write`).
- Ensure deterministic artifact naming by injecting a `PHOENIX_RUN_ID=$(date -u --iso-8601=seconds | TZ="America/Phoenix" date +"%Y-%m-%dT%H-%M-%S%z")` step and passing it to the CLI.

## Testing Expectations
- Unit test the permission script in `tests/github/test_check_comment_permissions.py` with fixture payloads covering: allowed member, outside collaborator, and missing command.
- Add a `tests/ops/test_workflow_templates.py` snapshot verifying required keys (triggers, env, jobs) using `ruamel.yaml` to parse the workflow without invoking GitHub.
- Provide a smoke test script in `scripts/github/simulate_orchestrator_event.sh` to run locally with sample payloads; ensure docs instruct exporting Phoenix TZ before execution.

## Documentation & Runbooks
- Update `docs/CI_CD/CodexIntegration.md` with the new workflow diagram and slash-command lifecycle.
- Extend `docs/promptops/orchestrator.md` to cover the workflow entrypoints, required secrets, and Phoenix time handling.
- Note the automation in `CHANGELOG.md` (Unreleased) and add a short summary to `docs/runbooks/orchestrator_dispatch.md`.

## Rollback & Observability
- Add job-level logging with `actions/github-script` to emit sanitized summaries (command text, issue, Phoenix timestamp) to the workflow summary.
- Define rollback steps: disable workflows via GitHub UI and revert `.github/workflows/*orchestrator*.yml`; confirm docs instruct deleting any uploaded artifacts.
- Provide metrics hooks by appending dispatch metadata to `artifacts/orchestrator/dispatch-log.ndjson` (one JSON line per run).

**Critic Check:**
- Lint/format/mypy pass? Coverage ≥ gate?
- No secrets logged; least-priv IAM?
- Phoenix cron/DST stated?
- Artifacts deterministic with run metadata?
