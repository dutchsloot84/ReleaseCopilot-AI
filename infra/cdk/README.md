# CDK Infrastructure

The AWS CDK application for ReleaseCopilot is configured via the repository root `cdk.json`. GitHub Actions relies on the
standard CDK CLI auto-discovery, so no additional wrappers or location checks are required. Keep the root file in sync with
any entry point changes (for example `infra/cdk/app.py`) to ensure CI and local commands behave the same way.

Local commands such as `cdk synth` or `cdk deploy` can be executed from the repository root without supplying `-a`. The
workflow installs the dependencies defined in `infra/cdk/requirements.txt` and then runs the CDK CLI directly.

## Core Stack Outputs

The `ReleaseCopilot-<env>-Core` stack provisions the S3 artifacts bucket,
Secrets Manager placeholders, Lambda functions, API Gateway webhook, and the
Jira DynamoDB cache. The cache table now uses a composite primary key of
`issue_key` (HASH) and `updated_at` (RANGE) with point-in-time recovery enabled
so that webhook replays remain idempotent. Global secondary indexes for
`FixVersionIndex`, `StatusIndex`, and `AssigneeIndex` are unchanged. Stack
outputs expose both the table name (`JiraTableName`) and ARN (`JiraTableArn`)
so IAM deploy roles can scope DynamoDB permissions precisely.

## Budget Alerts Configuration

The stack also manages a monthly AWS Budgets cost guardrail with SNS and email
notifications. Configure it through CDK context values:

| Context key | Purpose |
| --- | --- |
| `budgetAmount` | Monthly spend limit (float). |
| `budgetCurrency` | ISO currency code (defaults to `USD`). |
| `budgetEmailRecipients` | Comma-separated email recipients. |
| `budgetSnsTopicName` | Optional explicit SNS topic name (leave blank for generated). |
| `budgetExistingSnsTopicArn` | Reuse an existing SNS topic ARN instead of creating one. |

Deployments output `BudgetAlertsTopicArn`; persist it with run metadata to keep
alert routing deterministic across environments.
