# Notes & Decisions — #268 Fix CLI exports and align IAM policy Sid

_Repo:_ dutchsloot84/ReleaseCopilot-AI
_Source:_ https://github.com/dutchsloot84/ReleaseCopilot-AI/pull/268

- Decision (Uncategorized) — 2025-10-08 by @dutchsloot84
  Keep _attach_policies as the single source that composes the four inline IAM statements (including AllowSecretRetrieval) from the collected secret grants so the Lambda role always renders the expected SID set.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/pull/268#issuecomment-3379159307) <!-- digest:3ee67bb7eb3af1e06525f24c821f40460f2a7d904fd7bbce8618ab0155dd1a31 -->

- Note (Uncategorized) — 2025-10-08 by @dutchsloot84
  Regression tests lock in both the 4-SID policy layout and the repo-root .env precedence (find_dotenv_path), so rerun tests/infra/test_core_stack.py and tests/test_cli_args.py whenever touching these areas to catch deviations early.
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/pull/268#issuecomment-3379159307) <!-- digest:bc5bc161ef4600d9b4fdee82e88c6a6313ec184561394544b48446427b599da7 -->

- Action (Uncategorized) — 2025-10-08 by @dutchsloot84
  (Owner: Codex) Add a Historian digest entry reminding maintainers that SecretAccess.grant(..., attach_to_role=True) must continue feeding _attach_policies with explicit secret ARNs before merging future infrastructure changes
  [View comment](https://github.com/dutchsloot84/ReleaseCopilot-AI/pull/268#issuecomment-3379159307) <!-- digest:f5d3b5e6c15d8fd633734dc794814a5ebe25e1547a93979a83ae1d536a1d599b -->
