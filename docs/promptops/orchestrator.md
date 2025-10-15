# Wave 2 Orchestrator CLI

The Wave 2 orchestrator command chains helper prompts and dispatch automation from a single issue comment slash command. The CLI reads GitHub `issue_comment` payloads, validates Wave 2 labelling, and emits deterministic artifacts annotated with America/Phoenix timestamps (no DST adjustments required).

## Commands

### `rc orchestrator plan`
- Input: GitHub webhook payload (stdin or `--event-path`).
- Validates the issue has the `wave:wave2` label and that the comment body contains `/orchestrate` with a helper token (for example, `helper:276_Add_Orchestrator_workflow__slash-commands___dispatch_`).
- Produces `artifacts/orchestrator/<phoenix-timestamp>/plan.json`. Example directory: `artifacts/orchestrator/2024-05-12T09:30:00-07:00/plan.json`.
- Logs include `command=plan`, `issue_number`, and `phoenix_timestamp` for incident triage.

### `rc orchestrator dispatch`
- Input: `plan.json` created by the plan command (`--plan-path`).
- Prints the dispatch envelope (command + plan metadata) for downstream GitHub workflow triggers (`orchestrator-runner`).
- Structured logs echo `command=dispatch`, `issue_number`, and the Phoenix timestamp without exposing tokens.

## Expected Token Scope
The orchestrator commands only require GitHub tokens with `issues:read` to inspect labels and `workflow:write` to queue `orchestrator-runner`. Avoid using PATs with broader privileges.

## Smoke Test Checklist
1. Save a webhook fixture locally (for example `tests/fixtures/github_issue_comment_wave2.json`).
2. Ensure the helper prompt exists under `project/prompts/wave2/`.
3. Run `rc orchestrator plan --event-path fixture.json` and confirm the Phoenix timestamped artifact is created.
4. Run `rc orchestrator dispatch --plan-path <artifact>/plan.json` and verify the workflow name in stdout.

## Rollback Guidance
Reverting the commit that introduced the orchestrator command removes both CLI entry points. Remove any generated `artifacts/orchestrator/` directories manually during rollback to prevent stale plans from being consumed by automation.

## Observability
Logs leverage the shared `releasecopilot.logging_config` structured formatter. Every entry carries `command`, `issue_number`, and `phoenix_timestamp (America/Phoenix)`, supporting correlation with Phoenix-local cron scheduling.
