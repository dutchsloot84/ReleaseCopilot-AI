Use MOP: Wave 1 – Security/Costs/Storage.

Task: Implement **[Budget/Alarms] Low-Ceiling Budget + SNS Notice** as a single PR.
Branch: infra/billing-budget-sns

Acceptance Criteria:
- AWS Budgets with **50/80/100%** ACTUAL alerts.
- SNS/email recipients (configurable).
- Budget names include env.
- Manual notification verification documented.

Return the 5 outputs (plan, snippets, tests, docs, risk). Use L1 `AWS::Budgets::Budget` with 3 `NotificationsWithSubscribers`. Prefer context-driven config (e.g., `cdk.json` keys: `envName`, `budgetAmountUsd`, `budgetEmailRecipients`, `budgetSnsTopicArn`). Tests: CDK assertions confirm thresholds/subscriber types.
