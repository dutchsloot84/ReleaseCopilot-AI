# Codex and CI/CD Integration

Prompt waves rely on Codex-generated artifacts backed by CI enforcement.

## Codex Usage
- Codex runs the Master Orchestrator Prompt (MOP) followed by scoped sub-prompts in the active wave directories listed in `project/prompts/waves.json`.
- Each run records CLI arguments, default values, and Git SHA in the resulting Prompt Recipe.
- Prompt authors commit both the sub-prompt updates and their recipe to maintain parity.

## CI Enforcement
- **`validate_prompts.yml`**
  - Triggers on pull requests.
  - Uses `project/prompts/waves.json` to determine which waves enforce recipe coverage and executes `tools/validate_prompts.py` for each active wave.
  - Runs `ruff`, `black --check`, `mypy`, and `pytest --cov=. --cov-report=term-missing --cov-fail-under=70` for consistent linting and coverage gates.
- **`actions_comment.yml`**
  - Triggers on PR open and synchronize events.
  - Runs `tools/render_actions_comment.py` to read `actions/pending_actions.json`, render outstanding human actions, and apply labels.
- **`orchestrator-runner.yml`**
  - Listens for `/orchestrate` slash-commands or manual `workflow_dispatch` invocations.
  - Delegates execution to the reusable orchestrator dispatcher, which validates comment permissions before running.
  - Uploads deterministic Phoenix-timestamped artifacts for downstream auditing.

## Orchestrator Slash-Command Lifecycle

```mermaid
flowchart TD
    A[Maintainer comments /orchestrate] --> B{Permission check}
    B -->|Allowed (member/triage)| C[Reusable orchestrator workflow]
    B -->|Rejected| D[Exit with guidance]
    C --> E[Install rc CLI]
    E --> F[rc orchestrator dispatch]
    F --> G[Write dispatch-log.ndjson]
    G --> H[Upload Phoenix artifacts]
    H --> I[Publish workflow summary]
```

- All steps run with `TZ=America/Phoenix` to preserve Phoenix timestamps in logs and artifacts.
- The reusable workflow appends sanitized dispatch metadata to `artifacts/orchestrator/dispatch-log.ndjson` so the automation metrics remain deterministic.
- Maintain the allow-list for `/orchestrate` comments via repository variables such as `RELEASECOPILOT_MAINTAINERS`.

## Human Oversight
- Manual approvals remain in the loop via the action comment workflow.
- CI never stores secrets or tokens in logs; GitHub-provided tokens remain masked and are not echoed.

## Local Development
1. Install dependencies: `pip install -e .[dev]`.
2. Run formatters: `ruff check . && black --check .`.
3. Type check: `mypy` (modules touched).
4. Tests: `pytest --cov --cov-report=term-missing` (network calls must be mocked).

To smoke test the orchestrator locally, export `TZ=America/Phoenix` and run `scripts/github/simulate_orchestrator_event.sh`. The script reuses the same permission gate used in CI before writing Phoenix-normalized dispatch logs.

## Phoenix Time Standard
All timestamps in recipes, logs, and documentation use America/Phoenix (MST without DST).
Example: `2024-04-15 14:05 MST`.
