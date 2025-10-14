# Wave 2 – Sub-Prompt · [279] Generate Human Actions checklist + Runbook

**Context:** Use the active MOP; honor constraints & quality bar (Phoenix TZ: America/Phoenix).

**Acceptance Criteria (copy into PR):**
- Implement: Generate Human Actions checklist + Runbook (#279)
- Tests (no live network), ≥70% coverage on touched code; docs + CHANGELOG.
- PR markers: Decision / Note / Action.
- Phoenix TZ noted where schedulers/cron/log timestamps apply.

## Implementation Targets
- Create generator module `scripts/promptops/human_actions.py` that ingests the Wave 2 MOP + prioritized issues and emits:
  - `artifacts/human-actions/checklist.md` – Phoenix-local checklist with sections per helper/orchestrator workflow.
  - `artifacts/human-actions/calendar.json` – deterministic RFC 5545 (iCal) stub referencing America/Phoenix for reminders.
- Define structured inputs: `project/mop/wave2_mop.md` + `artifacts/top_issues.json`; provide CLI options for overrides.
- Include metadata (author, Phoenix timestamp, git SHA) at the top of each artifact; ensure reproducibility via sorted data.
- Add templated runbook under `docs/runbooks/wave2_human_actions.md` capturing manual verification paths, escalation contacts, and Phoenix business hours.
- Update `README.md` or `docs/runbooks/README.md` to link the new runbook; mention DST handling for Phoenix (no DST shift).
- Do not embed secrets; reference IAM roles symbolically (e.g., `arn:aws:iam::<acct>:role/releasecopilot-helpers`).

## Testing Expectations
- Write unit tests in `tests/promptops/test_human_actions.py` to verify deterministic output given fixture data (use snapshot comparison with golden files stored under `tests/golden/human-actions/`).
- Cover edge cases: empty issue list (emit stub), missing Wave 2 MOP (raise informative error), and timezone formatting.
- Ensure coverage thresholds remain ≥70%; update `tests/__init__.py` if new fixtures need registration.

## Documentation & Runbooks
- Document generator usage in `docs/promptops/human_actions.md`, including CLI invocation, artifact locations, and Phoenix time rationale.
- Add release notes to `CHANGELOG.md` summarizing the new human-actions automation.
- Include manual validation steps in the runbook referencing Phoenix office hours (UTC-7 year-round).

## Rollback & Observability
- Log generation metadata to `artifacts/human-actions/activity.ndjson`; include Phoenix timestamp + run hash.
- Provide rollback section instructing teams to delete generated artifacts and remove doc references if automation is reverted.
- Add preflight checklist in docs covering verification of artifact timestamps and absence of secret material.

**Critic Check:**
- Lint/format/mypy pass? Coverage ≥ gate?
- No secrets logged; least-priv IAM?
- Phoenix cron/DST stated?
- Artifacts deterministic with run metadata?
