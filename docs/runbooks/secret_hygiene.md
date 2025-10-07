# Secret Hygiene Runbook

This runbook documents how ReleaseCopilot operators manage the Secrets Manager
artifacts required for Jira and Bitbucket integrations.

## Required Secrets

All environments must define the following AWS Secrets Manager entries:

| Logical Name | Secrets Manager Name | Purpose |
| --- | --- | --- |
| `SECRET_JIRA` | `releasecopilot/jira/oauth` | OAuth credentials or API token for Jira access |
| `SECRET_BITBUCKET` | `releasecopilot/bitbucket/token` | Bitbucket API token or app password |
| `SECRET_WEBHOOK` | `releasecopilot/jira/webhook_secret` | Shared secret that authenticates Jira webhook deliveries |

These identifiers are exposed to Lambda functions via environment variables.
The values remain in AWS Secrets Manager and are never stored in plaintext.

## Redaction Expectations

Structured logs automatically redact keys containing `token`, `secret`,
`password`, `oauth`, or `apikey`. Use the helper in
`releasecopilot.utils.logging.redact_items` when logging dictionaries to avoid
accidentally surfacing sensitive material.

## Readiness Probe

Use the CLI to validate Secrets Manager connectivity without printing secret
values:

```bash
rc health readiness
```

The command prints `OK SECRET_*` entries when the Lambda-style environment is
configured correctly. Failures emit `FAIL SECRET_*` messages without revealing
secret payloads.

## Rotation Checklist

1. Rotate the secret in AWS Secrets Manager.
2. Deploy the updated value to the targeted environment.
3. Invoke `rc health readiness` locally or via Lambda to confirm access.
4. Capture screenshots of successful output for the release notes archive.
