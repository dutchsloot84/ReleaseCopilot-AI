# Prompt Recipes

Every active wave listed in `project/prompts/waves.json` with `"validate_recipes": true` must have accompanying recipes stored here.

| Sub-Prompt | Recipe |
|------------|--------|
| `project/prompts/archive/wave1/subprompt_budget_alarms.md` | `project/prompts/prompt_recipes/budget_alerts_recipe.md` |

Use `template.md` when creating new recipes. The validator reads the `Sub-Prompt Path` field inside each recipe to confirm coverage.
