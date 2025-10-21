# Jira Webhook Sync Runbook

**Decision:** Deploy production-grade Jira webhook sync with signature verification and correlation recompute.

**Note:** Secrets are retrieved from AWS; document rotation and local overrides.

**Action:** Implement webhook endpoint, normalize payloads, persist Phoenix-stamped artifacts, and update runbooks.

## Overview
The `/webhooks/jira` endpoint ingests Atlassian webhook deliveries, validates HMAC signatures, normalizes payloads, persists issue snapshots, and recomputes correlation artifacts. All operational timestamps use America/Phoenix (no DST).

## Prerequisites
- Configure the shared secret in AWS Secrets Manager (JSON key `jira_webhook_secret`) and expose its ARN via `JIRA_WEBHOOK_SECRET_ARN`.
- Ensure the DynamoDB table name is exported as `TABLE_NAME` for the Lambda/ASGI deployment.
- Set `RC_LOG_JSON=true` in environments where structured Phoenix logs are required.

## Setup
1. Rotate or provision the Atlassian webhook secret in AWS Secrets Manager.
2. Update `config/secrets.yml` (or environment overrides) with `JIRA_WEBHOOK_SECRET_ARN` so the service resolves the secret with `clients.secrets_manager.CredentialStore`.
3. Register the webhook endpoint in Atlassian pointing to `<deployment>/webhooks/jira` and paste the shared secret.
4. Verify that the Lambda or FastAPI service has IAM permissions for `secretsmanager:GetSecretValue` and DynamoDB write access.

## Phoenix-aware operations
- Signatures are validated with HMAC-SHA256. Structured logs emit `run_id`, `event_id`, and `generated_at` fields using `America/Phoenix`.
- Correlation artifacts are written to `artifacts/issues/wave3/jira_webhook/` using Phoenix timestamps in both metadata and per-issue entries.
- API responses include a `received_at` timestamp in Phoenix for traceability.

## Troubleshooting
- **Signature validation failures:** Confirm the Atlassian secret matches AWS Secrets Manager and that requests include the `X-Atlassian-Webhook-Signature` (or legacy `X-Atlassian-Signature`) header.
- **Repeated deliveries:** Artifacts capture `idempotency_key` usage; ensure DynamoDB conditional writes remain idempotent.
- **Correlation loops:** Check `artifacts/issues/wave3/jira_webhook/*.json` for the latest `run_id` metadata and the Phoenix `generated_at` timestamp. Use structured logs to inspect retries/backoff attempts.

## Rollback
1. Disable the `/webhooks/jira` endpoint in FastAPI/Flask or remove the API Gateway integration.
2. Revert the `services/jira_sync_webhook` deployment and remove the webhook secret from Atlassian.
3. Delete or archive `artifacts/issues/wave3/jira_webhook/` outputs if artifacts should not persist after rollback.
