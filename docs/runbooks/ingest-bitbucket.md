# Bitbucket Ingest Runbook (Wave 3)

## Overview

Wave 3 extends Release Copilot with Phoenix-aware Bitbucket ingest covering
scheduled scans and webhook deltas. The ingest pipeline persists commit metadata
(files changed, authorship, inferred story keys) into `data/bitbucket/commits.db`
using idempotent upserts keyed by commit hash. All generated artifacts log
America/Phoenix timestamps for compliance with the Mission Outline Plan.

## Scheduled scans

1. Ensure `config/settings.yaml` (or your override file) defines:
   - `bitbucket.workspace`
   - `bitbucket.repositories`
   - `bitbucket.default_branches`
   - `bitbucket.credentials` (username + app password or OAuth token)
2. Run the scan command locally:

   ```bash
   rc ingest bitbucket-scan --hours 4
   ```

   Optional overrides:

   - `--config <path>` for non-default configuration files.
   - `--repos repo-1 repo-2` to target a subset of repositories.
   - `--branches main develop` to restrict branch inclusion.
   - `--database data/bitbucket/commits.db` to point at an alternate SQLite
     location.

3. Inspect the generated artifact under
   `artifacts/issues/wave3/bitbucket/scan_<run_id>.json`. Each run records the
   scan window, Phoenix timestamp, git SHA, and summarized payload entries.

## Webhook ingestion

### FastAPI

```python
from fastapi import FastAPI
from releasecopilot.ingest.storage import CommitStorage
from services.webhooks.bitbucket import register_bitbucket_webhook

app = FastAPI()
storage = CommitStorage("data/bitbucket/commits.db")
register_bitbucket_webhook(app, storage=storage, secret="super-secret")
```

### Flask

```python
from flask import Flask
from releasecopilot.ingest.storage import CommitStorage
from services.webhooks.bitbucket import register_bitbucket_webhook

app = Flask(__name__)
storage = CommitStorage("data/bitbucket/commits.db")
register_bitbucket_webhook(app, storage=storage, secret="super-secret")
```

Webhook handlers expect the `X-Webhook-Secret` header when `secret` is provided
and accept Bitbucket `repo:push`, `pullrequest:created`,
`pullrequest:updated`, and `pullrequest:fulfilled` events. Payloads are reduced
to commit upserts stored alongside story keys derived from commit messages,
branch names, and PR titles.

## Artifacts

All runs emit JSON artifacts in `artifacts/issues/wave3/bitbucket/` conforming
to `artifacts/issues/wave3/bitbucket/run.schema.json`. Verify the `timezone`
field remains `America/Phoenix` and that sensitive data (tokens, secrets) never
appears in the payload. Each artifact contains:

- `run_id` – unique identifier for the ingest execution.
- `git_sha` – repository state when the scan completed.
- `window.start` / `window.end` – Phoenix timestamps defining the scan window.
- `payload` – commit summaries with authorship, branch, file changes, and story
  keys.

## Operational considerations

- **Rate limits** – The Bitbucket client automatically retries on 429/5xx
  responses using exponential backoff. For sustained throttling, reduce the
  `--hours` window or split repositories across staggered runs.
- **Idempotency** – Commits are keyed by SHA. Replaying the same webhook or scan
  updates `last_seen_at` without duplicating records.
- **Secrets** – Configure the Bitbucket webhook secret in AWS Secrets Manager
  (e.g. `releasecopilot/bitbucket/webhook_secret`) and surface it through
  environment variables when deploying the webhook service.
- **Monitoring** – Review Phoenix-stamped logs under `temp_data/bitbucket/` and
  artifact metadata to confirm ingest cadence.
