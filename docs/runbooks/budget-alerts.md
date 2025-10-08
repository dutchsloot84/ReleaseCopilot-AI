# Budget Alerts Runbook

## Overview
Budget alerts notify the team when AWS spending crosses defined thresholds for the current month.

## TLS-only publishing
The `BudgetAlerts` SNS topic enforces TLS for all publishers. Any publish request that is not sent with secure transport (`aws:SecureTransport=false`) is denied by the resource policy. Use HTTPS/TLS clients when integrating with the topic.

## Operations
- Deploy or update the infrastructure with `cdk deploy`.
- Capture the `BudgetAlertsTopicArn` output and store it with the deployment metadata.
- After deployment, publish a test message using an HTTPS client to confirm the policy allows TLS publishers.

## Incident response
1. Review CloudWatch metrics and alarms related to cost budgets.
2. If alerts are missing, verify that publishers are using TLS when sending messages.
3. Re-deploy the stack if policy drift is detected.

## Rollback
If a legitimate publisher cannot use TLS, revert the policy statement commit and redeploy the stack. Document any exceptions and work with the publisher to restore secure transport.

## Time zone
Unless otherwise noted, times are tracked in America/Phoenix.
