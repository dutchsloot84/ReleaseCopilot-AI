# CI Watchdog

The CI Watchdog workflow keeps an eye on failing pull request checks and
nudges contributors when the pipeline breaks. It runs every day at
14:00 UTC (07:00 America/Phoenix, no daylight saving time) and can also
be triggered manually via the **Run workflow** button or with the
`/watchdog autofix` slash command.

## Workflow overview

The workflow lives at `.github/workflows/ci-watchdog.yml` and uses the
`ORCHESTRATOR_BOT_TOKEN` with least-privileged scopes (`checks:read`,
`pull_requests:write`). It never logs secrets. The jobs are:

- **scan** – calls `scripts/github/ci_watchdog.py` to collect failing
  checks for open pull requests updated within the past 72 hours. The
  job writes deterministic artifacts to `artifacts/watchdog/<phoenix-date>/status.json`,
  appends to `artifacts/watchdog/activity-log.ndjson`, and emits
  `artifacts/watchdog/metrics.json` with counter data.
- **report** – renders Markdown via `render_report` and comments the
  summary on each affected pull request. A sanitized Phoenix timestamp
  and failure counts are also published to the workflow summary for easy
  triage.
- **autofix** – runs only when explicitly gated by `/watchdog autofix`
  (see below). It invokes `scripts/github/run_watchdog_autofix.sh` to run
  `ruff check --fix`, `black`, and a targeted `pytest` selection, all without
  network access.

## Rollback plan

If the watchdog needs to be disabled:

1. Pause the schedule through the GitHub UI or comment out the `schedule`
   block (the workflow also honours manual dispatches).
2. Revert `.github/workflows/ci-watchdog.yml` to the previous revision.
3. Remove any generated state under `artifacts/watchdog/` to keep the
   repository clean.

These steps can be completed without affecting other CI/CD automation.
