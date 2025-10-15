# Orchestrator Dispatch Runbook

## Summary
- Slash-command entrypoint (`/orchestrate`) routes through `.github/workflows/orchestrator-runner.yml` and the reusable dispatcher.
- Permission enforcement relies on `scripts/github/check_comment_permissions.py`, which honours Phoenix timezone metadata in all logs.
- Artifacts and workflow summaries are timestamped with America/Phoenix to align with the prompt-ops schedule.

## Preconditions
- `ORCHESTRATOR_BOT_TOKEN` secret must exist with `issues:read` and `workflows:write` scopes.
- Repository variable `RELEASECOPILOT_MAINTAINERS` contains a comma-separated list of trusted maintainers.
- Phoenix timezone exported in local terminals (`export TZ=America/Phoenix`) before running smoke tests.

## Triggering a Run
1. Navigate to the issue that needs orchestration.
2. Post `/orchestrate <options>` as a new comment.
3. Confirm the `Orchestrator Runner` workflow starts within a minute. Manual retries can use the `Run workflow` button in the Actions tab.

## Observability
- Workflow summary contains sanitized fields (command, issue, Phoenix timestamp) via `actions/github-script`.
- Structured metadata accumulates in `artifacts/orchestrator/dispatch-log.ndjson`; download the artifact named `orchestrator-<PHOENIX_RUN_ID>` for auditing.
- Local smoke tests use `scripts/github/simulate_orchestrator_event.sh` and require Phoenix timezone exports to match CI output.

## Rollback
- Disable `orchestrator-runner` and `reusable-orchestrator` workflows in the GitHub Actions UI or revert the workflow files.
- Delete artifacts uploaded under `orchestrator-*` to prevent stale metadata from triggering downstream automations.
- Remove any cached Phoenix log directories under `artifacts/orchestrator/` after download.
