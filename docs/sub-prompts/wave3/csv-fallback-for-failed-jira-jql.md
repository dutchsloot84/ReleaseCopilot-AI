# Wave 3 – Sub-Prompt · [AUTO] CSV Fallback for Failed Jira JQL

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- On JQL failure (after retries), prompt for CSV path and continue.
- Clear CLI messaging; graceful errors for bad paths/CSV.
- Tests for success/failure paths.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Update `clients/jira_client.py` retry logic to raise a typed `JiraJQLFailed` exception after exhausting retries.
- In `src/releasecopilot/cli.py` (audit command), catch `JiraJQLFailed` and prompt via `click.prompt` for a CSV fallback path, validating existence and schema.
- Add CSV loader helper `src/releasecopilot/utils/jira_csv_loader.py` to parse issues deterministically (UTF-8, no network) and integrate with downstream processors.
- Ensure Phoenix-aware logging when reporting fallback usage (include `datetime.now(ZoneInfo("America/Phoenix"))` in status message if timestamped).
- Sequence: define exception → update CLI prompt → implement CSV loader → integrate with processors → add tests/docs.

### Key code snippets
```python
# clients/jira_client.py excerpt
class JiraJQLFailed(RuntimeError):
    """Raised when Jira JQL queries fail after configured retries."""


def search(self, jql: str) -> list[dict[str, Any]]:
    try:
        return self._do_search(jql)
    except HTTPError as error:
        if self._retries_exhausted(error):
            raise JiraJQLFailed(f"JQL failed after retries: {jql}") from error
        raise
```

```python
# src/releasecopilot/cli.py excerpt
from zoneinfo import ZoneInfo


@cli.command()
def audit(...):
    try:
        issues = jira_client.search(jql)
    except JiraJQLFailed:
        csv_path = Path(click.prompt("JQL failed. Provide CSV export path", type=click.Path()))
        phoenix_now = datetime.now(tz=ZoneInfo("America/Phoenix")).isoformat(timespec="seconds")
        click.echo(f"[{phoenix_now}] Loading issues from CSV fallback: {csv_path}")
        issues = load_issues_from_csv(csv_path)
```

```python
# src/releasecopilot/utils/jira_csv_loader.py
def load_issues_from_csv(path: Path) -> list[dict[str, Any]]:
    """Read Jira issues from CSV export deterministically."""

    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader]
```

### Tests (pytest; no live network)
- `tests/clients/test_jira_client.py::test_search_raises_after_retries` to confirm `JiraJQLFailed` is raised.
- `tests/cli/test_audit_csv_fallback.py::test_audit_prompts_for_csv_on_failure` uses `CliRunner` with monkeypatched prompt.
- `tests/utils/test_jira_csv_loader.py::test_load_issues_from_csv_handles_missing_columns` ensures graceful error messaging.
- Edge cases: nonexistent file path, invalid CSV headers, partial data, Phoenix timestamp formatting.
- Achieve ≥70% coverage across new CLI branch via targeted tests and fixtures under `tests/fixtures/jira/`.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/jira.md`:

> If Jira JQL queries fail after retries, the CLI prompts for a local CSV export. Provide the path to a Jira export generated with the standard column set; the fallback is logged with an America/Phoenix timestamp for traceability.

Update `README.md` troubleshooting section:

> Use `rc audit --jira-csv path/to/export.csv` to bypass JQL failures locally. CSV files must be UTF-8 encoded and match the default Jira export headers.

### Risk & rollback
- Risks: CSV schema drift causing processor errors, confusing prompts, timezone formatting inconsistencies.
- Rollback: revert exception/prompt changes in Jira client and CLI; remove CSV loader module.
- No data migrations or dependency updates introduced.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Run ruff/black/mypy after adding the new helper; execute pytest CLI and utils suites.
- Confirm prompts avoid echoing sensitive JQL/credentials.
- Validate fallback logging includes Phoenix timestamp.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Provide CSV fallback flow when Jira JQL retries fail.
- **Note:** CSV exports must include the default Jira columns for ingestion.
- **Action:** Raise typed exception, prompt user for CSV path, and document fallback usage.