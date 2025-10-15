## [Unreleased]
### Added
- Wave 2 orchestrator CLI with slash-command planning, Phoenix-stamped artifacts,
  and dispatch envelopes for the `orchestrator-runner` workflow.
- GitHub Action automation for `/orchestrate` commands, including Phoenix-timestamped artifacts,
  reusable dispatcher workflow, and comment permission gating.
- Phoenix-ready S3 artifacts bucket hardening: TLS-only bucket policy, bucket-owner enforced ownership, structured prefixes with lifecycle management, and read/write managed policies.
- Artifacts bucket runbook documenting prefix retention, Phoenix-time procedures, and recovery guidance.
- Least-privilege Secrets Manager wiring with secret smoke test CLI and redaction helpers.
- MOP + prompt-chaining scaffolding (`prompts/` templates, runbooks, PR template, Issue form).
- Active MOP index in docs; README quickstart.
- Wave 1 prompt recipe catalog, human-in-the-loop tracking JSON, and CI validation/comment automation.
- Monthly AWS Budgets cost guardrail with SNS/email alerts and manual verification runbook.

### Chore
- Remove placeholderless f-strings flagged by ruff F541.

### Fixed
- Expose CLI functions at the package root to satisfy tests and document the
  supported public interface.
- Align the IAM secrets retrieval policy Sid with infrastructure assertions to
  maintain least-privilege access checks.
- Prefer repository-root `.env` files over package-local ones when
  bootstrapping the CLI environment to honour dotenv precedence expectations.
- Deduplicate Secrets Manager inline policies so exactly four statements remain
  in the synthesized template, matching the Wave 1 least-privilege contract.
- Restore the ``AllowSecretRetrieval`` Sid with explicit secret ARNs while
  keeping the inline policy confined to four least-privilege statements.
- Enforce TLS-only publishing on the BudgetAlerts SNS topic to resolve
  AwsSolutions-SNS3.
