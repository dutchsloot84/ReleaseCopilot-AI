# Wave 2 Orchestrator CLI

The Wave 2 orchestrator command chains helper prompts and dispatch automation from a single issue comment slash command. The CLI reads GitHub `issue_comment` payloads, validates Wave 2 labelling, and emits deterministic artifacts annotated with America/Phoenix timestamps (no DST adjustments required).

## Commands

### `rc orchestrator plan`
- Input: GitHub webhook payload (stdin or `--event-path`).
- Validates the issue has the `wave:wave2` label and that the comment body contains `/orchestrate` with a helper token (for example, `helper:276_Add_Orchestrator_workflow__slash-commands___dispatch_`).
- Produces `artifacts/orchestrator/<phoenix-timestamp>/plan.json`. Example directory: `artifacts/orchestrator/2024-05-12T09:30:00-07:00/plan.json`.
- Logs include `command=plan`, `issue_number`, and `phoenix_timestamp` for incident triage.

### `rc orchestrator dispatch`
- Input: `plan.json` created by the plan command (`--plan-path`). When invoked by GitHub Actions the workflow forwards the raw
  webhook payload via `--event-path` so the CLI can derive the matching plan automatically.
- Prints the dispatch envelope (command + plan metadata) for downstream GitHub workflow triggers (`orchestrator-runner`).
- Structured logs echo `command=dispatch`, `issue_number`, and the Phoenix timestamp without exposing tokens.

## Workflow Entrypoints
- **`.github/workflows/orchestrator-runner.yml`** listens for `/orchestrate` slash-commands or manual `workflow_dispatch`
  requests and delegates to the reusable workflow.
- **`.github/workflows/reusable-orchestrator.yml`** performs the permission gate, installs dependencies, runs
  `rc orchestrator dispatch`, and uploads Phoenix-normalized artifacts.
- **`scripts/github/check_comment_permissions.py`** enforces that only actors with `MEMBER`, `OWNER`, or `TRIAGE` associations
  (or an allow-listed maintainer username) can dispatch orchestration. Production jobs populate the allow-list using a cached
  export from the `releasecopilot-maintainers` team, avoiding live API calls during execution.

## Required Secrets and Variables
- `ORCHESTRATOR_BOT_TOKEN` (secret): GitHub token with the minimal scopes `issues:read` and `workflows:write` used by the
  reusable workflow. The token is injected into the CLI via environment variable and never echoed to logs.
- `RELEASECOPILOT_MAINTAINERS` (repository/organization variable): comma-separated list of GitHub usernames synchronized from
  the maintainers team. The permission check reads this list to allow trusted collaborators even if their association is not
  elevated to `MEMBER`.

## Phoenix Time Handling
- All orchestrator automation explicitly exports `TZ=America/Phoenix` to ensure timestamps do not observe DST changes.
- Workflow steps compute a `PHOENIX_RUN_ID` using the Phoenix timezone, which is reused for artifact names, summary output, and
  appended to `artifacts/orchestrator/dispatch-log.ndjson` for deterministic observability.
- When running smoke tests locally, set `export TZ=America/Phoenix` prior to executing any scripts so timestamps match the CI
  expectation.

## Expected Token Scope
The orchestrator commands only require GitHub tokens with `issues:read` to inspect labels and `workflow:write` to queue `orchestrator-runner`. Avoid using PATs with broader privileges.

## Smoke Test Checklist
1. Save a webhook fixture locally (for example `tests/fixtures/github_issue_comment_wave2.json`).
2. Ensure the helper prompt exists under `project/prompts/wave2/`.
3. Export the Phoenix timezone: `export TZ=America/Phoenix`.
4. Run `rc orchestrator plan --event-path fixture.json` and confirm the Phoenix timestamped artifact is created.
5. Run `rc orchestrator dispatch --plan-path <artifact>/plan.json` and verify the workflow name in stdout, or execute
   `scripts/github/simulate_orchestrator_event.sh` to replay the GitHub workflow locally without hitting the network.

## Rollback Guidance
To disable automation temporarily, pause the `orchestrator-runner` workflow via the GitHub UI or revert both orchestrator
workflow files (`.github/workflows/orchestrator-runner.yml` and `.github/workflows/reusable-orchestrator.yml`). Remove any
generated `artifacts/orchestrator/` directories manually during rollback to prevent stale plans from being consumed by
automation. Delete uploaded workflow artifacts from the GitHub Actions UI to complete the rollback.

## Observability
Logs leverage the shared `releasecopilot.logging_config` structured formatter. Every entry carries `command`, `issue_number`, and `phoenix_timestamp (America/Phoenix)`, supporting correlation with Phoenix-local cron scheduling.
