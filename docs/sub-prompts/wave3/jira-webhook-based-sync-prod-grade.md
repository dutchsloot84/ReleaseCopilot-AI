# Wave 3 – Sub-Prompt · [AUTO] Jira Webhook-based Sync (Prod-grade)

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- HMAC/signature validation; normalized payload schema.
- Idempotent upsert; structured logs; retries/backoff.
- Recompute correlation for touched issues.
- Docs: setup, troubleshooting, Phoenix timestamps.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Implement webhook endpoint in `services/webhooks/jira.py` validating HMAC signatures using shared secret stored via `clients/secrets_manager.py`.
- Normalize payload schema with a serializer in `src/releasecopilot/jira/webhook_parser.py` that extracts issue keys, fields, and updated timestamps.
- Persist payloads using idempotent upsert via `processors/audit_processor.py` or new `src/releasecopilot/jira/sync.py`, ensuring retries/backoff around Jira follow-up fetches.
- Trigger correlation recomputation by calling `src/matcher/engine.match` for touched issues and storing results in `artifacts/issues/wave3/jira_webhook/` with Phoenix timestamps.
- Update logging configuration to ensure structured JSON logs (with `run_id`, `event_id`, `generated_at` in America/Phoenix).
- Sequence: secret retrieval + signature validation → payload normalization → persistence/upsert logic → correlation recompute hook → artifact/log wiring → documentation/tests.

### Key code snippets
```python
# services/webhooks/jira.py
from fastapi import APIRouter, Header, HTTPException
from zoneinfo import ZoneInfo


@router.post("/webhooks/jira")
async def jira_webhook(payload: dict[str, Any], x_atlassian_signature: str = Header(...)) -> dict[str, str]:
    if not verify_signature(secret=secrets.get("jira_webhook"), body=payload, signature=x_atlassian_signature):
        raise HTTPException(status_code=401, detail="invalid signature")
    normalized = normalize_payload(payload)
    upsert_issue(normalized)
    recompute_correlation(issue_keys=normalized.issue_keys)
    phoenix_now = datetime.now(tz=ZoneInfo("America/Phoenix")).isoformat(timespec="seconds")
    return {"status": "ok", "received_at": phoenix_now}
```

```python
# src/releasecopilot/jira/webhook_parser.py
def normalize_payload(event: Mapping[str, Any]) -> JiraWebhook:
    """Return deterministic Jira webhook model from raw Atlassian payload."""

    issue = event["issue"]
    return JiraWebhook(
        issue_key=issue["key"],
        changelog=event.get("changelog", {}),
        updated_at=parse_datetime(issue["fields"]["updated"]),
    )
```

```json
// artifacts/issues/wave3/jira_webhook/run.schema.json (excerpt)
{
  "type": "object",
  "required": ["run_id", "git_sha", "generated_at", "timezone", "issues"],
  "properties": {
    "timezone": {"const": "America/Phoenix"},
    "issues": {"type": "array", "items": {"type": "object", "required": ["issue_key", "updated_at"]}}
  }
}
```

### Tests (pytest; no live network)
- `tests/webhooks/test_jira_signature.py::test_verify_signature_accepts_valid_payload` covers HMAC validation.
- `tests/webhooks/test_jira_signature.py::test_verify_signature_rejects_invalid_payload` ensures 401 behavior.
- `tests/jira/test_webhook_parser.py::test_normalize_payload_extracts_required_fields` uses cached fixtures.
- `tests/jira/test_sync.py::test_recompute_correlation_called_for_touched_issues` patches matcher engine.
- Edge cases: missing changelog, repeated webhook deliveries, retries/backoff using `tenacity` mocks.
- Maintain coverage by running `pytest tests/webhooks tests/jira --cov=src/releasecopilot/jira --cov=services/webhooks`.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/jira-webhooks.md`:

> Configure the Jira webhook secret via AWS Secrets Manager and set `JIRA_WEBHOOK_SECRET_ARN` in `config/secrets.yml`. The `/webhooks/jira` endpoint validates Atlassian signatures and logs Phoenix timestamps (America/Phoenix) for each received event. Correlation is recomputed automatically for touched issues.

Troubleshooting section:

> If webhooks fail signature validation, confirm the secret matches the Atlassian configuration. Check `artifacts/issues/wave3/jira_webhook/` for the latest Phoenix-stamped run metadata and review structured logs for retries/backoff attempts.

### Risk & rollback
- Risks: signature validation bugs causing dropped events, correlation recompute loops, schema drift in webhook payloads.
- Rollback: disable `/webhooks/jira` route, revert parser/upsert modules, and remove artifact updates; clear stored secrets if necessary.
- No data migrations introduced; existing correlation engine remains intact if webhook flow rolled back.


## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Run ruff/black/mypy across webhook modules; execute pytest with coverage to ensure retry/backoff paths exercised.
- Verify structured logs omit tokens/secrets while including run metadata.
- Confirm documentation references Phoenix timestamps and setup steps.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Deploy production-grade Jira webhook sync with signature verification and correlation recompute.
- **Note:** Secrets are retrieved from AWS; document rotation and local overrides.
- **Action:** Implement webhook endpoint, normalize payloads, persist Phoenix-stamped artifacts, and update runbooks.
