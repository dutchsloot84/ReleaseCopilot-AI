# Prompt Wave Workflow

```
Master Orchestrator Prompt (Wave N)
        |
        v
   Sub-Prompt (project/prompts/waveN)
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
Wave prompts coordinate focus areas (for example Wave 1 Security/Cost/Storage or Wave 2 Orchestrator adoption). Each sub-prompt traces back to the active Master Orchestrator Prompt (MOP) and results in deterministic artifacts:

1. **Sub-Prompt Authoring** – Prompt authors extend `project/prompts/<wave>` with scoped tasks that reference the wave's MOP.
2. **Prompt Recipes** – Every sub-prompt must have an accompanying recipe detailing the orchestration, validations, and human approvals. Recipes live beside the prompts and include Phoenix timestamps (America/Phoenix).
3. **Human Actions** – Manual follow-ups are logged in `actions/pending_actions.json`, rendered into PR comments, and closed via "done ✅" replies.
4. **CI/CD Hooks** – GitHub Actions enforce prompt-to-recipe parity across every active wave, run lint/tests (`black`, `ruff`, `mypy`, `pytest`), and ensure coverage ≥ 70%.
5. **Historian Update** – Completed changes publish Decision/Note/Action markers and snapshot metadata for audit trails.

## Author Workflow
- Start from the MOP for your wave (for example `project/prompts/wave2/README.md` or `project/prompts/wave1/mop_wave1_security.md`) and craft or update a sub-prompt.
- Create or refresh the Prompt Recipe using the template.
- Record manual approvals or verifications in `actions/pending_actions.json` with Phoenix deadlines.
- Submit a PR that references the recipe, includes the Decision/Note/Action markers in the description, and calls out the wave label. Use the canonical `Decision:`/`Note:`/`Action:` prefixes (and `Blocker:` if applicable) so Codex and human-authored PRs stay consistent.
- Monitor CI; resolve validator or action comment feedback before merging.

## Run Metadata Expectations
All automation that emits files or comments records:
- CLI arguments and defaults.
- Git SHA of the run.
- Timestamp in America/Phoenix.

Example timestamp notation: `2024-04-15 14:05 MST`.

## Wave 2 Helper Automation

Use `python -m scripts.github.wave2_helper` to manage the helper backlog for Wave 2. The CLI supports `collect`, `prioritize`, `seed`, `post`, and `open-pr` subcommands, each writing deterministic artifacts under `artifacts/helpers/` and `project/prompts/wave2/`. See `docs/promptops/helpers.md` for detailed usage. When preparing manual comments or PRs, keep the Decision / Note / Action markers and include Phoenix-local scheduling context (America/Phoenix) in every timestamp.

## Prompt Wave CI Validation

- GitHub Actions exposes a reusable job named **Validate Prompt Waves**. The workflow reads `project/prompts/waves.json` for entries marked with `"validate_recipes": true`, validates recipe coverage for each active wave, and then runs the shared lint/test gate (`ruff`, `black --check`, `mypy`, `pytest --cov`).
- Run the validator locally with `python tools/validate_prompts.py --waves wave2` to scope to a specific wave, or omit `--waves` to lint every directory enabled in `waves.json`. Passing `--prompts-dir` manually is still supported for ad-hoc validation.
- When adding a new wave, update `waves.json` with the wave name/path and flip `"validate_recipes"` to `true` once prompt recipes exist. The CI matrix will pick it up automatically.

## Wave 2 Orchestrator Entry Points
Wave 2 helpers are dispatched via the CLI:

```bash
rc orchestrator plan --event-path path/to/issue_comment.json
rc orchestrator dispatch --plan-path artifacts/orchestrator/<timestamp>/plan.json
```

Both commands log the Phoenix timestamp and issue number for traceability and align with the Wave 2 runbook documented in `docs/promptops/orchestrator.md`.
