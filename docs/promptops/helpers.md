# Wave 2 Helper Automation

The Wave 2 helper CLI streamlines backlog triage, deterministic artifact generation, and manual follow-up prep for the active Master Orchestrator Prompt (MOP). The commands live in `scripts/github/wave2_helper.py` and can be executed with `python -m scripts.github.wave2_helper`.

## Commands

| Command | Purpose | Key Inputs | Outputs |
| --- | --- | --- | --- |
| `collect` | Fetch Wave 2 issues from GitHub (or `--issues-json` during offline runs) and filter by helper labels. | `GITHUB_TOKEN` (if live), optional `--issues-json` path. | `artifacts/helpers/issues.json` |
| `prioritize` | Rank filtered issues using label weights from `config/wave2_helper.yml`. | `artifacts/helpers/issues.json` or `--issues-json`. | `artifacts/helpers/prioritized-issues.json` with metadata |
| `seed` | Merge prioritized issues with Wave 2 MOP constraints to create prompt templates. | `artifacts/helpers/prioritized-issues.json` or `--issues-json`. | Prompt files under `project/prompts/wave2/` |
| `post` | Generate Markdown comment drafts that include Phoenix scheduling placeholders. | `artifacts/helpers/prioritized-issues.json` or `--issues-json`. | `artifacts/helpers/comments/<ISSUE>.md` |
| `open-pr` | Scaffold a branch suggestion and PR body ready for manual review. | `artifacts/helpers/prioritized-issues.json` or `--issues-json`. | `artifacts/helpers/pr_template.md` |

All commands emit structured logs via `releasecopilot.logging_config` and append audit entries to `artifacts/helpers/activity-log.ndjson`. Every log and artifact timestamp is recorded in **America/Phoenix** to match the Wave 2 scheduling rhythm and to avoid DST surprises.

## Configuration

`config/wave2_helper.yml` describes the label weights, helper maintainers, target labels, and artifact directories. The `artifact_dirs.base` value anchors the remaining relative paths so every helper artifact stays under `artifacts/helpers/` by default. Tests may override the configuration file, but production usage should rely on the checked-in defaults. Update the configuration if new helper labels or maintainers are introduced.

## Phoenix Timezone Rationale

Wave 2 automation coordinates follow-ups with Phoenix-based maintainers. Each artifact embeds a Phoenix timestamp (`America/Phoenix`) so schedulers, cron jobs, and human notes align with the documented wave cadence. Comment drafts intentionally include placeholders reminding operators to confirm Phoenix availability before posting.

## Audit Trail and Deterministic Artifacts

Each command writes an entry to `artifacts/helpers/activity-log.ndjson` with a deterministic UUID (namespace UUID5 of command + timestamp). Artifacts are JSON-encoded with stable sorting to ensure diffs remain predictable. Prompt files repeat the Decision / Note / Action expectations from the active MOP so downstream contributors follow the required reporting format.

## Rollback

To undo the helper automation:

1. Delete generated helper artifacts under `artifacts/helpers/` (issues, prioritized payloads, comments, activity log, and PR template) plus any seeded prompt files created for the run.
2. Remove the CLI re-export (`wave2_helper_cli`) from `scripts/github/__init__.py` to decouple the helper from packaged modules.
3. Update documentation referencing this helper (including this page and the MOP workflow doc) if the tool is decommissioned.

Running the commands with `--issues-json` remains safe for offline validation or CI since no live network calls occur when the flag is provided.
