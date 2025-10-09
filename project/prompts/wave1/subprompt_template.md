**Context (do not alter):** Use the active MOP. Honor constraints & quality bar (lint/format, mypy, pytest w/o network, coverage gate, docs, CHANGELOG, PR markers; least-priv IAM; no secrets in logs; Phoenix time).

**Task:** Implement **[PR Title]** as a single PR.
**Branch:** feat/<area>-<short-name>
**Acceptance Criteria:** (copy from the MOP item verbatim)

**Return these 5 outputs:**
1) Diff-oriented plan (files; function/class signatures; CDK/IAM if applicable).
2) Key code snippets (enough to implement).
3) Tests (file names + specimen cases; mocks/fixtures; no live network).
4) Docs excerpt (README and/or runbook).
5) Risk & rollback (what to verify in CI/CloudWatch; revert path).

**PR markers to include:**
- Decision: <key choice & rationale>
- Note: <operator tip and where to look>
- Action: <owner + target date>
