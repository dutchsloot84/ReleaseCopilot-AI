---
id: mop-wave1-security
version: 1.1.0
owner: Shayne
status: active
last_review: 2025-10-06
---

# Wave 1: Security / Costs / Storage

## Purpose
Harden the landing zone: Secrets in AWS SM with least-privilege access, low-ceiling Budgets + SNS/email alerts, and a secure S3 artifacts bucket.

## Global constraints
- Least-privilege IAM; **no secrets in logs**.
- Phoenix time (document DST behavior when scheduling).
- Deterministic artifacts with run metadata (timestamp, env, commit SHA).

## Quality bar (all PRs)
- Lint/format: ruff + black.
- mypy baseline on touched modules.
- pytest with **no live network**; ≥70% coverage with PR comment.
- README/docs update + CHANGELOG entry.
- PR includes **Decision / Note / Action** markers.

## Sequenced PRs
1) **[Secrets]** Create & wire SM secrets + Lambda read + smoke test + `.env.example`.
2) **[Budget/Alarms]** Monthly cost budget with **50/80/100% ACTUAL** alerts → SNS/email; names include env; manual delivery verification documented.
3) **[S3 Artifact Bucket]** Block-public ON, SSE-S3, lifecycle 30→IA, 90→Glacier; prefix convention documented.

## Artifacts & traceability
- Docs in `docs/` (runbooks under `docs/runbooks/`).
- `.env.example` documents secret **names** (values only in SM).
- CDK outputs (where applicable) surface relevant ARNs.
