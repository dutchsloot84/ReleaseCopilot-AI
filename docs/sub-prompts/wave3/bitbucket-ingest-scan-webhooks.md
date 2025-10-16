# Wave 3 – Sub-Prompt · [AUTO] Bitbucket Ingest (scan + webhooks)

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Time-window commit scan across configured repos.
- Webhooks: push/PR created/updated/fulfilled.
- Store files_changed and authorship; idempotent upsert.
- Key extraction from message/branch/PR title.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Add a `src/clients/bitbucket_client.py` enhancement to expose time-window commit scans leveraging the REST API with pagination and `modified_on` filters; respect `ZoneInfo("America/Phoenix")` when translating schedule windows.
- Create `src/releasecopilot/ingest/bitbucket_scanner.py` handling repository iteration, storing `files_changed` and authorship into persistence (e.g., `data/bitbucket/commits.db` via existing storage helpers) with idempotent upsert keyed by commit hash.
- Introduce a webhook handler module `src/releasecopilot/ingest/bitbucket_webhooks.py` processing push and PR events (created/updated/fulfilled) and extracting keys from commit messages, branch names, and PR titles using existing matcher utilities.
- Update CLI entry (e.g., `rc ingest bitbucket-scan`) in `src/releasecopilot/cli.py` to trigger scheduled scans and register FastAPI/Flask webhook route under `services/webhooks/bitbucket.py` if present.
- Ensure artifacts/logging under `artifacts/issues/wave3/bitbucket/` capture Phoenix timestamps plus run metadata without secrets.
- Sequence: client pagination updates → scanner service writing idempotent storage → webhook processor → CLI/route wiring → artifact/log validation → tests/docs.

### Key code snippets
```python
# src/releasecopilot/ingest/bitbucket_scanner.py
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def scan_commits(*, client: BitbucketClient, repos: list[str], hours: int = 24, tz: ZoneInfo | None = None) -> list[dict[str, str]]:
    """Return commits modified within the Phoenix-aware window.

    Uses deterministic pagination (page size 50) and logs only commit hashes/metadata.
    """

    timezone = tz or ZoneInfo("America/Phoenix")
    window_start = datetime.now(tz=timezone) - timedelta(hours=hours)
    collected: list[dict[str, str]] = []
    for repo in repos:
        for commit in client.iter_commits(repo=repo, since=window_start):
            collected.append(
                {
                    "hash": commit["hash"],
                    "author": commit["author"]["raw"],
                    "files_changed": [file["path"] for file in commit.get("files", [])],
                    "repository": repo,
                }
            )
    return collected
```

```diff
# src/releasecopilot/ingest/bitbucket_webhooks.py
@@
def handle_push(event: Mapping[str, Any]) -> list[CommitUpsert]:
    """Normalize Bitbucket push payloads for idempotent storage."""
    commits: list[CommitUpsert] = []
    for change in event.get("push", {}).get("changes", []):
        branch = change.get("new", {}).get("name")
        for commit in change.get("commits", []):
            keys = extract_story_keys(commit.get("message", ""), branch)
            commits.append(
                CommitUpsert(
                    hash=commit["hash"],
                    repository=event["repository"]["full_name"],
                    files_changed=[entry["path"] for entry in commit.get("files", [])],
                    authorship=commit["author"].get("raw"),
                    story_keys=keys,
                )
            )
    return commits
```

```json
// artifacts/issues/wave3/bitbucket/run.schema.json (excerpt)
{
  "type": "object",
  "required": ["run_id", "git_sha", "generated_at", "timezone", "payload"],
  "properties": {
    "timezone": {"const": "America/Phoenix"},
    "payload": {"type": "array", "items": {"type": "object", "required": ["hash", "repository"]}}
  }
}
```

### Tests (pytest; no live network)
- `tests/ingest/test_bitbucket_scanner.py::test_scan_commits_with_pagination` mocks the client iterator to ensure pagination stops deterministically and Phoenix window filtering works.
- `tests/ingest/test_bitbucket_webhooks.py::test_handle_push_extracts_story_keys` covers key extraction from message/branch.
- `tests/ingest/test_bitbucket_webhooks.py::test_pr_events_idempotent_upsert` verifies PR created/updated/fulfilled payload deduplication.
- Edge cases: empty files arrays, missing authorship, duplicate commits, timezone boundary at midnight Phoenix.
- Use cached webhook fixtures under `tests/fixtures/bitbucket/` to maintain determinism and achieve ≥70% coverage on new modules.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/ingest-bitbucket.md`:

> Configure Bitbucket ingest by setting workspace, repositories, and webhook secret in `config/bitbucket.yml`. Scheduled scans respect America/Phoenix windows; run `rc ingest bitbucket-scan --hours 4` for ad-hoc backfills. Webhooks (push, PR created/updated/fulfilled) post to `/webhooks/bitbucket` and populate idempotent commit stores with `files_changed` and authorship metadata.

Update `README.md` integration timeline section:

> Wave 3 Bitbucket ingest combines periodic scans with webhook deltas. All artifacts log `run_id`, `git_sha`, and Phoenix timestamps for compliance.

### Risk & rollback
- Risks: API rate limits causing partial scans, webhook retries creating duplicates, timezone misalignment leading to missed commits.
- Rollback: disable webhook route, revert `src/releasecopilot/ingest/` modules, and remove CLI entry; clear generated artifacts if they reference the new runner.
- No data migrations are performed; existing storage tables remain unchanged.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Validate signature verification for webhooks (if configured) and confirm retries handled safely.
- Run ruff/black/mypy and pytest with coverage on ingest modules.
- Inspect artifacts/logs for run metadata only; redact commit messages if secrets detected.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Enable Bitbucket scans and webhooks with Phoenix-aware windows and idempotent storage.
- **Note:** Webhook secrets should remain in AWS Secrets Manager; document local `.env` usage for development.
- **Action:** Implement scanner/webhook handlers, wire CLI/route, and validate artifacts/logging.