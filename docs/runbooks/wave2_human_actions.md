# Wave 2 Human Actions Runbook

This runbook accompanies the human actions generator and captures manual steps required
for Wave 2 orchestrator and helper workflows. Phoenix business hours are 09:00–17:00
America/Phoenix (UTC-7 year-round, no daylight saving time).

## Contacts

| Role | Contact | Notes |
| --- | --- | --- |
| Orchestrator DRI | orchestrator@releasecopilot.test | Primary escalation during Phoenix business hours. |
| Helper Lead | helpers@releasecopilot.test | Coordinates helper availability and manual validations. |
| PromptOps On-Call | arn:aws:iam::<acct>:role/releasecopilot-helpers | IAM role assumed for Phoenix interventions. |

Escalations after 17:00 Phoenix should go to the PromptOps on-call rotation.

## Manual verification

1. Review `artifacts/human-actions/checklist.md` and confirm metadata (author, git SHA,
   run hash) matches the latest release branch.
2. Validate checklist sections:
   - Orchestrator items reference current slash-command workflows.
   - Helper items cover backlog, prioritization, and sub-prompt follow-ups.
   - Human oversight or general sections document escalation paths.
3. Inspect `artifacts/human-actions/calendar.json`:
   - Ensure each event is scheduled between 09:00 and 17:00 Phoenix.
   - Confirm the `DTSTART` values use `TZID=America/Phoenix` and the generated `DTSTAMP`
     remains in UTC.
   - Import the iCal stub into a calendar sandbox if changes are significant.
4. Check `artifacts/human-actions/activity.ndjson` for the latest entry:
   - Phoenix timestamp should match the checklist header.
   - Run hash must match the checklist metadata for traceability.
   - Issue numbers align with the prioritized list used for the run.
5. Cross-reference prioritized issues with the active MOP section to verify no manual
   blockers remain.

## Phoenix scheduling notes

- Phoenix operates on Mountain Standard Time (UTC-7) all year. Do **not** adjust events
  for DST transitions.
- Cron or scheduler integrations should specify `TZ=America/Phoenix` explicitly.
- Manual reminders should default to 15 minutes before the scheduled 09:00–17:00 window.

## Rollback steps

1. Delete generated human action artifacts (`checklist.md`, `calendar.json`,
   `activity.ndjson`).
2. Remove the runbook and generator documentation references (including README links).
3. Notify orchestrator and helper stakeholders that automation has been reverted.
4. Disable any pipelines or cron jobs that invoke `scripts.promptops.human_actions`.

## Observability and audit

- Store generated artifacts in version control for traceability.
- Keep activity log entries for at least 90 days to satisfy audit requirements.
- Capture manual validation outcomes in team retrospectives.
