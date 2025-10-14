# Wave 2 – Sub-Prompt · [276] Add Orchestrator workflow (slash-commands + dispatch)

**Context:** Use the active MOP; honor constraints & quality bar (Phoenix TZ: America/Phoenix).

**Acceptance Criteria (copy into PR):**
- Implement: Add Orchestrator workflow (slash-commands + dispatch) (#276)
- Tests (no live network), ≥70% coverage on touched code; docs + CHANGELOG.
- PR markers: Decision / Note / Action.
- Phoenix TZ noted where schedulers/cron/log timestamps apply.

## Implementation Targets
- Extend the ReleaseCopilot CLI with an `orchestrator` command:
  - Add `src/cli/orchestrator.py` exposing `register_orchestrator_parser()` and `run_orchestrator_command()`.
  - Wire the new command into `src/cli/app.py` with entry points for `rc orchestrator plan` and `rc orchestrator dispatch`.
  - Accept inputs from GitHub issue comment payloads (JSON from stdin or `--event-path`). Parse `/orchestrate` slash commands, validate label `wave:wave2`, and derive the target issue + helper sub-prompt.
- Create `src/releasecopilot/orchestrator/command.py` defining dataclasses for `SlashCommand`, `DispatchPlan`, and `DispatchEnvelope` with deterministic `to_dict()` output (Phoenix timestamps via `ZoneInfo("America/Phoenix")`).
- Persist command artifacts under `artifacts/orchestrator/<timestamp-phoenix>/plan.json` using ISO-8601 with timezone offset; ensure directories are created idempotently.
- Implement minimal dispatch planning logic that maps issues → helper prompt files in `project/prompts/wave2/` and returns the GitHub workflow name to trigger (`orchestrator-runner`). No network calls inside the planner.
- Guard logs so that tokens/secret names are never echoed; rely on structured logging via `releasecopilot.logging_config`.

## Testing Expectations
- Add unit coverage in `tests/cli/test_orchestrator_cli.py` for CLI parsing, invalid command text, and event ingestion from fixture JSON.
- Add serialization tests in `tests/releasecopilot/orchestrator/test_command.py` ensuring Phoenix timezone formatting and deterministic dict ordering.
- Mock filesystem interactions with `pyfakefs` or `tmp_path` fixtures to confirm artifact paths are respected.
- Update `pytest.ini` if new markers are introduced; keep total coverage ≥70% on touched modules.

## Documentation & Runbooks
- Document the CLI flow in `docs/promptops/orchestrator.md`, including sample Phoenix timestamps and how artifacts are named.
- Update `docs/promptops/MOP_Workflow.md` to reference the new CLI entry points for Wave 2 orchestration.
- Record release notes in `CHANGELOG.md` under the current Unreleased section.

## Rollback & Observability
- Add structured logging fields (`command`, `issue_number`, `phoenix_timestamp`) to simplify debugging; respect least-priv IAM by documenting the expected token scope in `docs/promptops/orchestrator.md`.
- Provide rollback notes: reverting to commit prior to this change disables the CLI command; ensure documentation describes manual cleanup of any generated artifacts.
- Include a smoke-test checklist in the PR description for verifying `rc orchestrator plan --event-path sample.json` locally.

**Critic Check:**
- Lint/format/mypy pass? Coverage ≥ gate?
- No secrets logged; least-priv IAM?
- Phoenix cron/DST stated?
- Artifacts deterministic with run metadata?
