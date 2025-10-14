# Notes & Decisions — #116 [Secrets] Create & Wire Jira/Bitbucket/Webhook Secrets (SM)

_Repo:_ dutchsloot84/ReleaseCopilot-AI
_Source:_ https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/116

- Decision (Completed) — 2025-10-07 by @dutchsloot84
  Grant Lambdas read-only GetSecretValue to three explicit Secret ARNs via SecretAccess; expose secret names as env.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/116#issuecomment-3378830511) <!-- digest:7ac7edd8f957d5da812e55e7a2b8ed4a3b2f8124f242c3d5f604699cdeb90d30 -->

- Note (Completed) — 2025-10-07 by @dutchsloot84
  Values never logged; readiness prints only OK/FAIL; tests mock boto3 (no network).
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/116#issuecomment-3378830511) <!-- digest:d20f0585c57c25d60b9ccb3389a16da96df421b02879333935af7da9ec236d8e -->

- Action (Completed) — 2025-10-07 by @dutchsloot84
  (Owner: Shayne, 2025-10-08) Create three SM secrets and run `rc health readiness`; attach runbook screens.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/116#issuecomment-3378830511) <!-- digest:0cc536493ee42951ca3d7aa02116e72c0572a3099651c58d5f144c840527081f -->
