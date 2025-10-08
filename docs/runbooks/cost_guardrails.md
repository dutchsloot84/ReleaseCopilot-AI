# Cost Guardrails (Budgets + Alerts)

The core stack provisions an AWS Budgets monthly cost budget that emits alerts
at 50 %, 80 %, and 100 % of the configured spend limit. Alerts flow to both an
SNS topic (forwarded to downstream automation) and direct email recipients.

## Configuration

- Configure the budget amount, currency, email recipients, and optional SNS
  topic name via CDK context (`budgetAmount`, `budgetCurrency`,
  `budgetEmailRecipients`, and `budgetSnsTopicName`).
- To wire an existing SNS topic, set `budgetExistingSnsTopicArn` and leave the
  name blank. The stack will skip topic creation and reuse the provided ARN.
- Stack names incorporate the deployment environment (for example,
  `releasecopilot-dev-monthly-cost`) to keep multi-environment budgets
  disambiguated.

## Manual Verification (Phoenix Time)

1. Deploy the stack and capture the `BudgetAlertsTopicArn` output from the CDK
   synthesis or deployment logs. Store it with the release metadata so future
   runs stay deterministic.
2. In the AWS console, open **Billing → Budgets → Cost budgets** and confirm the
   `releasecopilot-<env>-monthly-cost` entry shows three ACTUAL alert thresholds
   (50 %, 80 %, 100 %).
3. Select the budget and choose **Actions → Edit notifications**. Use **Send
   test email/SNS notification** for each subscriber. AWS Budgets operates on a
   Phoenix-time basis: production alerts can take up to 8 hours to arrive, so
   rely on the manual test button instead of forcing spend.
4. For SNS delivery, publish a test message to the topic via the console while
   observing the downstream subscription endpoints (for example, Slack or
   ticketing integrations). Document the timestamp of the successful delivery
   in the release record.

## Troubleshooting

- If manual notifications fail, confirm the SNS topic allows the
  `budgets.amazonaws.com` service principal to publish. The generated topic
  includes this policy; legacy topics may need a manual update.
- Budgets are global to the AWS account. The console defaults to `us-east-1`,
  but alerts remain account-wide regardless of the UI region selector.
