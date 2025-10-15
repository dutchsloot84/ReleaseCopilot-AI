# Wave 1 MOP Workflow

```
Master Orchestrator Prompt (Wave 1)
        |
        v
   Sub-Prompt (project/prompts/wave1)
        |
        v
   Prompt Recipe (project/prompts/prompt_recipes)
        |
        v
Pull Request (Decision / Note / Action markers)
        |
        v
 Historian & Release Records
```

## Overview
Wave 1 coordinates Security, Cost, and Storage initiatives. Each sub-prompt traces back to the active Master Orchestrator Prompt (MOP) and results in deterministic artifacts:

1. **Sub-Prompt Authoring** – Prompt authors extend `project/prompts/wave1` with scoped tasks that reference the Wave 1 MOP.
2. **Prompt Recipes** – Every sub-prompt must have an accompanying recipe detailing the orchestration, validations, and human approvals. Recipes live beside the prompts and include Phoenix timestamps (America/Phoenix).
3. **Human Actions** – Manual follow-ups are logged in `actions/pending_actions.json`, rendered into PR comments, and closed via "done ✅" replies.
4. **CI/CD Hooks** – GitHub Actions enforce prompt-to-recipe parity, run lint/tests (`black`, `ruff`, `mypy`, `pytest`), and ensure coverage ≥ 70%.
5. **Historian Update** – Completed changes publish Decision/Note/Action markers and snapshot metadata for audit trails.

## Author Workflow
- Start from the MOP (`project/prompts/wave1/mop_wave1_security.md`) and craft or update a sub-prompt.
- Create or refresh the Prompt Recipe using the template.
- Record manual approvals or verifications in `actions/pending_actions.json` with Phoenix deadlines.
- Submit a PR that references the recipe and includes the Decision/Note/Action markers in the description.
- Monitor CI; resolve validator or action comment feedback before merging.

## Run Metadata Expectations
All automation that emits files or comments records:
- CLI arguments and defaults.
- Git SHA of the run.
- Timestamp in America/Phoenix.

Example timestamp notation: `2024-04-15 14:05 MST`.

## Wave 2 Orchestrator Entry Points
Wave 2 helpers are dispatched via the CLI:

```bash
rc orchestrator plan --event-path path/to/issue_comment.json
rc orchestrator dispatch --plan-path artifacts/orchestrator/<timestamp>/plan.json
```

Both commands log the Phoenix timestamp and issue number for traceability and align with the Wave 2 runbook documented in `docs/promptops/orchestrator.md`.
