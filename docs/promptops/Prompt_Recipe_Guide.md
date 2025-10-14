# Prompt Recipe Guide

Prompt Recipes explain how Codex executed a sub-prompt and which manual steps remain. They create an auditable chain from prompts to deployments.

## When to Write a Recipe
- Every `project/prompts/wave1/*.md` sub-prompt (excluding README files) must have a companion recipe.
- Update the recipe whenever the automation changes or new human-in-the-loop actions are introduced.

## Template Walkthrough
1. **Purpose & Wave** – Describe why the work exists and confirm the MOP wave alignment.
2. **Sub-Prompt Path** – Relative path consumed by the validator. Ensure it matches the actual file name.
3. **Triggering Issue/PR** – Reference the issue or PR (e.g., `#2`).
4. **Phoenix Timestamp** – Use America/Phoenix timezone for reproducibility.
5. **Steps Executed** – List Codex orchestration and CI validations in order.
6. **Human Notes** – Reference any entries in `actions/pending_actions.json`.
7. **Re-run Instructions** – Document CLI args, defaults, and Git SHA for deterministic reruns.
8. **Validation Checklist** – Confirm lint, tests, coverage, and action updates.
9. **Decisions/Notes/Actions** – Mirror the PR markers.
10. **Output Artifacts** – Point to generated files, PR comments, and historian entries.

## Best Practices
- Keep technical detail concise but explicit (mention policy names, stack IDs, etc.).
- Link to documentation in `docs/promptops` when referencing processes.
- Record CLI commands exactly as run, including defaults.
- When multiple sub-prompts share a recipe, note the full list in the `Sub-Prompt Path` field separated by commas.

## Referencing Recipes in PRs
Include a **Note** marker in the PR body linking to the recipe, e.g.:
```
Note: Prompt recipe → project/prompts/prompt_recipes/budget_alerts_recipe.md
```
This ensures reviewers can trace automation steps quickly.
