# Prompt Recipe Template

- **Purpose:** <describe why this recipe exists>
- **MOP Wave:** <e.g., Wave 1 – Security/Costs/Storage>
- **Sub-Prompt Path:** <relative path such as `project/prompts/wave1/subprompt_budget_alarms.md`>
- **Triggering Issue/PR:** <link or identifier>
- **Phoenix Timestamp Prepared:** <2025-01-15 10:00 MST>

## Steps Executed
1. <Codex orchestration step>
2. <CI/CD automation step>
3. ...

## Human-in-the-Loop Notes
- Action JSON entry IDs (if any): <list>
- Approvals or manual checks required: <details>

## Re-run Instructions
- CLI invocation (record args + defaults): `<cmd --flag=value>`
- Required context files or environment variables: <list>
- Git SHA used for baseline: `<sha>`

## Validation Checklist
- [ ] Prompt validated via `tools/validate_prompts.py`
- [ ] Tests executed (`pytest -q`, coverage ≥ 70%)
- [ ] Linting (`ruff`, `black --check`, `mypy`)
- [ ] Pending actions updated/confirmed

## Decisions / Notes / Actions
- **Decision:** <summary of the key decision>
- **Note:** <important implementation detail>
- **Action:** <follow-up work or verification>

## Output Artifacts
- Generated files: <list>
- PR Comment links: <link>
- Release/Historian references: <link>

---

### Example (Budget Alerts)
- **Purpose:** Document how Budget alerting with SNS was rolled out.
- **MOP Wave:** Wave 1 – Security/Costs/Storage
- **Sub-Prompt Path:** project/prompts/wave1/subprompt_budget_alarms.md
- **Triggering Issue/PR:** #2

Steps include orchestrating AWS Budgets resources, validating SecureTransport enforcement, writing the Prompt Recipe, and capturing manual SNS delivery verification in `actions/pending_actions.json`.
