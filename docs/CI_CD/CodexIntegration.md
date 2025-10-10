# Codex and CI/CD Integration

Wave 1 automation relies on Codex-generated artifacts backed by CI enforcement.

## Codex Usage
- Codex runs the Master Orchestrator Prompt (MOP) followed by scoped sub-prompts in `project/prompts/wave1`.
- Each run records CLI arguments, default values, and Git SHA in the resulting Prompt Recipe.
- Prompt authors commit both the sub-prompt updates and their recipe to maintain parity.

## CI Enforcement
- **`validate_prompts.yml`**
  - Triggers on pull requests.
  - Executes `tools/validate_prompts.py` to ensure every sub-prompt has a recipe that cites its path.
  - Runs `ruff`, `black --check`, `mypy`, and `pytest -q` with coverage ≥ 70% (configured via `pytest.ini`).
- **`actions_comment.yml`**
  - Triggers on PR open and synchronize events.
  - Runs `tools/render_actions_comment.py` to read `actions/pending_actions.json`, render outstanding human actions, and apply labels.

## Human Oversight
- Manual approvals remain in the loop via the action comment workflow.
- CI never stores secrets or tokens in logs; GitHub-provided tokens remain masked and are not echoed.

## Local Development
1. Install dependencies: `pip install -r requirements-dev.txt`.
2. Run formatters: `ruff check . && black --check .`.
3. Type check: `mypy` (modules touched).
4. Tests: `pytest --cov --cov-report=term-missing` (network calls must be mocked).

## Phoenix Time Standard
All timestamps in recipes, logs, and documentation use America/Phoenix (MST without DST).
Example: `2024-04-15 14:05 MST`.
