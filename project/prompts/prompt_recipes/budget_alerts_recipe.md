# Budget Alerts + SNS Prompt Recipe

- **Purpose:** Capture how Wave 1 implemented low-ceiling AWS Budget alerts with SNS notifications.
- **MOP Wave:** Wave 1 – Security/Costs/Storage
- **Sub-Prompt Path:** project/prompts/archive/wave1/subprompt_budget_alarms.md
- **Triggering Issue/PR:** #2
- **Phoenix Timestamp Prepared:** 2024-04-15 09:30 MST

## Steps Executed
1. Codex consumed the sub-prompt and generated CDK constructs for the `BudgetAlertsTopic` stack.
2. CI provisioned unit tests validating the `AWS::Budgets::Budget` thresholds and SNS subscribers.
3. A manual SecureTransport policy review was requested and tracked in `actions/pending_actions.json`.
4. pytest suite ran with network mocking to confirm no live AWS traffic.

## Human-in-the-Loop Notes
- Action JSON entry IDs (if any): `Wave 1 #2`
- Approvals or manual checks required: Confirm SNS topic policy enforces `aws:SecureTransport` and document notification delivery in PR notes.

## Re-run Instructions
- CLI invocation (record args + defaults): `python -m tools.deploy_budget_alerts --env=prod --defaults-from=cdk.json`
- Required context files or environment variables: `cdk.json`, `.env.example` for recipients, AWS credentials with least-privilege (Budgets + SNS write).
- Git SHA used for baseline: `8323d83e0999c9b91ffaf508a9e541dcccf4d24c`

## Validation Checklist
- [x] Prompt validated via `tools/validate_prompts.py`
- [x] Tests executed (`pytest -q`, coverage ≥ 70%)
- [x] Linting (`ruff`, `black --check`, `mypy`)
- [x] Pending actions updated/confirmed

## Decisions / Notes / Actions
- **Decision:** Enforce `aws:SecureTransport` in the SNS topic resource policy before enabling subscriptions.
- **Note:** Delivery verification remains manual; attach CloudWatch Logs evidence to the PR.
- **Action:** Track SecureTransport approval in `actions/pending_actions.json` and close once the security team comments “done ✅”.

## Output Artifacts
- Generated files: `infra/cdk/budget_alerts_stack.py`, updated tests under `tests/infra/test_budget_alerts.py`.
- PR Comment links: SecureTransport approval thread (Wave 1 #2).
- Release/Historian references: Recorded in `reports/historian/wave1/budget_alerts.json`.
