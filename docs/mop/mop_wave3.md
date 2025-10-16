# Wave 3 Mission Outline Plan

_Generated at 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST)_

## Purpose
Deliver MVP surface: Streamlit dashboard, webhook-grade Jira/Bitbucket ingest, core correlation/gaps, QA heuristics, and export artifacts — with Phoenix-anchored timestamps and deterministic generator outputs.

## Global Constraints
- Least-privilege IAM.
- No secrets in logs.
- Phoenix time handling in schedulers/timestamps.
- No live network in tests (use cached payloads/fixtures).
- Reproducible artifacts (args/git_sha/generated_at captured).

## Quality Bar
- ruff + black clean, mypy passes.
- pytest with ≥70% coverage on touched code.
- Docs updated (README/runbooks), CHANGELOG updated.
- Artifacts: JSON/Excel with run_id, git_sha, generated_at.

## Sequenced PRs
- **Streamlit MVP Dashboard v1 (Nov ’25 lane)** — 4 acceptance checks
  - Tabs: Audit, Gaps, QA Focus, Artifacts.
  - Header shows Nov ’25 stats (stories, commits, linked %, gaps).
  - Actions: Re-sync Jira, Re-scan Repos, Recompute Correlation.
  - Download buttons: Release Notes, Validation Doc, JSON, Excel.
  _Notes:_
  - Keep components minimal (tables/cards); no vendor lock-in.
- **Jira Webhook-based Sync (Prod-grade)** — 4 acceptance checks
  - HMAC/signature validation; normalized payload schema.
  - Idempotent upsert; structured logs; retries/backoff.
  - Recompute correlation for touched issues.
  - Docs: setup, troubleshooting, Phoenix timestamps.
- **Bitbucket Ingest (scan + webhooks)** — 4 acceptance checks
  - Time-window commit scan across configured repos.
  - Webhooks: push/PR created/updated/fulfilled.
  - Store files_changed and authorship; idempotent upsert.
  - Key extraction from message/branch/PR title.
- **Correlation & Gaps Engine** — 4 acceptance checks
  - Link rules: message > branch > PR title.
  - Gaps endpoints: stories-without-commits, commits-without-story.
  - Persist run metadata (args, git_sha, generated_at).
  - Unit tests for edge cases/collisions.
- **QA Focus & Regression Heuristics (YAML-driven)** — 4 acceptance checks
  - risk.yaml with critical_paths + label_weights.
  - Score per story/module with reasons; top N endpoint.
  - UI list with reason tooltips; JSON export section.
  - Artifacts: Release Notes + Validation Doc + Exports.
- **Artifacts: Release Notes + Validation Doc + Exports** — 4 acceptance checks
  - Release Notes grouped by type; links to issues.
  - Validation Doc uses Deployment Notes field (configurable ID).
  - JSON/Excel include run_id, git_sha, generated_at.
  - UI download buttons wired.
- **Agents (Optional): LangGraph minimal path** — 4 acceptance checks
  - requirements-agents.txt; src/agents/langgraph/ with AuditAgentGraph.
  - Wrap deterministic nodes; add LLM summary/risk narrative node.
  - Phoenix-stamped JSON in artifacts/orchestrator/.
  - Orchestrator dispatch supports ‘langgraph-runner’; UI shows narrative.
  _Notes:_
  - Pin temperature/seed; redact secrets; document opt-in install.
- **CSV Fallback for Failed Jira JQL** — 3 acceptance checks
  - On JQL failure (after retries), prompt for CSV path and continue.
  - Clear CLI messaging; graceful errors for bad paths/CSV.
  - Tests for success/failure paths.
- **[Tests] Mocked Jira/Bitbucket + E2E with cached payloads** — 3 acceptance checks
  - Clients covered for pagination, errors, retries (no network).
  - E2E audit using cached fixtures verifies schema + content.
  - Contract tests guard JSON/Excel schema (jsonschema + column checks).
- **[CI] Coverage Gate + PR Summary Comment** — 2 acceptance checks
  - pytest-cov ≥70% on touched code; build fails otherwise.
  - PR comment posts coverage summary.
- **PR Template + Orchestration Docs (slash-commands, Phoenix TZ)** — 3 acceptance checks
  - Template enforces Decision/Note/Action markers.
  - Notes quality bar, ≥70% coverage, ruff/black/mypy gates.
  - Docs page explains orchestrator plan/dispatch and Phoenix TZ.
- **[Pre-commit] ruff, black, mypy** — 2 acceptance checks
  - .pre-commit-config.yaml lands; README has install steps.
  - pre-commit run --all-files passes in CI.

## Artifacts & Traceability
- MOP source: `backlog/wave3.yaml`
- Rendered MOP: `docs/mop/mop_wave3.md`
- Sub-prompts: `docs/sub-prompts/wave3/`
- Issue bodies: `artifacts/issues/wave3/`
- Manifest: `artifacts/manifests/wave3_subprompts.json`
- Generated via `make gen-wave3` with Phoenix timestamps.

## Notes & Decisions Policy
- Capture contributor annotations with **Decision:**/**Note:**/**Action:** markers.
- America/Phoenix (no DST) timestamps must accompany status updates.
- Store generated artifacts in Git with deterministic ordering.

## Acceptance Gate
- Validate linting, typing, and tests before marking this wave complete.
- Ensure the manifest SHA (`git_sha`) matches the release commit used for generation.