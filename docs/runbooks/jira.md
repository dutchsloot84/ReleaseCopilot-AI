# Jira Incident Response – JQL Failures

**Decision:** Provide CSV fallback flow when Jira JQL retries fail. See [`artifacts/issues/wave3/csv-fallback-for-failed-jira-jql.md`](../../artifacts/issues/wave3/csv-fallback-for-failed-jira-jql.md) for the originating Wave 3 manifest entry.
**Note:** CSV exports must include the default Jira columns (Issue key, Summary, Status) so downstream processors receive the expected schema.
**Action:** When the audit CLI exhausts JQL retries, provide a local Jira CSV export path when prompted. The fallback emits an America/Phoenix timestamp in the console and structured logs for traceability.

## CSV fallback procedure

1. Observe the Phoenix-stamped prompt similar to `[2025-10-15T07:30:00-07:00] Loading issues from CSV fallback: /path/to/export.csv` after JQL retries fail.
2. Generate a Jira CSV export with the default column set (Issue key, Summary, Status, Assignee, Issue Type) and UTF-8 encoding.
3. Re-run the prompt if the path is invalid or the schema check fails; the CLI prints the failure reason before re-prompting.
4. Proceed with the audit run—the loader maps each CSV row into a Jira-like payload so `processors/audit_processor.py` can consume the data without further changes.

The fallback path is appended to the raw artifact bundle so the resulting Phoenix timestamp and CSV source remain available for auditors.
