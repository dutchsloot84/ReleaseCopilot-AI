# Wave 2 Human Actions Generator

The Wave 2 human actions generator automates checklist, calendar, and activity logging
artifacts derived from the active Master Orchestrator Prompt (MOP) and the prioritized
issue list.

## Why Phoenix time?
All timestamps are normalized to the `America/Phoenix` timezone (UTC-7 year-round).
Phoenix does **not** observe daylight saving time, which keeps reminders and checklists
stable across seasons for the helpers and orchestrator teams.

## CLI usage

Run the generator from the repository root:

```bash
python -m scripts.promptops.human_actions \
  --author "ReleaseCopilot PromptOps" \
  --git-sha "$(git rev-parse HEAD)" \
  --timestamp "2025-10-15T09:00:00-07:00"
```

### Options

| Option | Description | Default |
| --- | --- | --- |
| `--mop-path` | Path to the Wave 2 MOP markdown file. | `project/mop/wave2_mop.md` |
| `--issues-path` | Path to the prioritized issues JSON payload. | `artifacts/top_issues.json` |
| `--output-dir` | Directory that will receive the generated artifacts. | `artifacts/human-actions` |
| `--author` | Author metadata embedded in each artifact. | `PromptOps Automation` |
| `--timestamp` | ISO-8601 timestamp (with offset) used for Phoenix-local scheduling. | Current Phoenix time |
| `--git-sha` | Commit SHA embedded in metadata. | `unknown` |

All artifacts are deterministic: repeated runs with the same inputs and metadata produce
identical outputs.

## Generated artifacts

| File | Purpose |
| --- | --- |
| `artifacts/human-actions/checklist.md` | Phoenix-local checklist grouped by orchestrator and helper workflows with manual validation notes. |
| `artifacts/human-actions/calendar.json` | RFC 5545 compliant iCal payload (serialized to JSON) for scheduling reminders in `America/Phoenix`. |
| `artifacts/human-actions/activity.ndjson` | Append-only log capturing Phoenix timestamps, run hashes, and involved issue numbers. |

## Preflight checklist

Before delivering artifacts, manually verify:

1. Checklist and calendar metadata list the expected author, Git SHA, and Phoenix timestamp.
2. Calendar entries align with Phoenix (UTC-7) business hours and do not contain DST shifts.
3. No secrets, credentials, or sensitive URLs appear in generated content; only issue metadata is referenced.
4. Activity log entries match the git SHA and run hash from the checklist header.

## Rollback guidance

If the automation needs to be reverted:

1. Delete the generated artifacts under `artifacts/human-actions/`.
2. Remove documentation references, including this guide and the associated runbook link.
3. Notify PromptOps stakeholders and revert any cron or scheduler integrations that point to the generated calendar.
