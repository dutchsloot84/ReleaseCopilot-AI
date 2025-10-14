# Notes & Decisions — #267 [Wave 1] Fix CLI exports + IAM policy assertion to restore CI

_Repo:_ dutchsloot84/ReleaseCopilot-AI
_Source:_ https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/267

- Note (Uncategorized) — 2025-10-08 by @dutchsloot84
  “Standardized IAM SIDs (4 only). Avoid per-role duplication of GetSecretValue statements.”
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/267#issuecomment-3379112353) <!-- digest:4485a6cf886b9759ad0b4d97fc2ee669f79c5176b89852752c750f1ccdf9af17 -->

- Decision (Uncategorized) — 2025-10-08 by @dutchsloot84
  Reinstate AllowSecretRetrieval with explicit secret ARNs and consolidate IAM into a single inline policy of exactly four SIDs.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/267#issuecomment-3379112353) <!-- digest:8e177071d3920b91d997a7c3afbe4eaa914a7458bc4a9c9fd29c194c76949278 -->

- Note (Uncategorized) — 2025-10-08 by @dutchsloot84
  No wildcard secret resources; GetSecretValue only; removed duplicate per-role policy adds.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/267#issuecomment-3379112353) <!-- digest:32d9761e9e4f6ef31ff1e6cb5993ba3ef511e29a1513130b33d69454928103b0 -->

- Action (Uncategorized) — 2025-10-08 by @dutchsloot84
  (Owner: Shayne) Run cdk synth and attach the rendered policy section; confirm CI green and update Historian digest.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/issues/267#issuecomment-3379112353) <!-- digest:c4c45b9bc00b5864827a23c0cdf8c641a1fb3e82fb47104444197e47cc7dfbb1 -->
