"""Budget alert construct for ReleaseCopilot cost guardrails."""

from __future__ import annotations

from typing import Iterable, Sequence

from aws_cdk import aws_budgets as budgets, aws_iam as iam, aws_sns as sns
from constructs import Construct


class BudgetAlerts(Construct):
    """Provision a monthly cost budget with SNS and email notifications."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        budget_amount: float,
        currency: str = "USD",
        email_recipients: Sequence[str] | None = None,
        sns_topic_name: str | None = None,
        existing_topic_arn: str | None = None,
    ) -> None:
        super().__init__(scope, construct_id)

        if budget_amount <= 0:
            raise ValueError("budget_amount must be positive")

        self.environment_name = environment_name
        self.budget_amount = budget_amount
        self.currency = currency

        normalized_env = environment_name.replace(" ", "-").lower()
        topic_id = "BudgetAlertsTopic"

        if existing_topic_arn:
            self.topic = sns.Topic.from_topic_arn(self, topic_id, existing_topic_arn)
            topic_arn = existing_topic_arn
            can_add_policy = False
        else:
            topic = sns.Topic(
                self,
                topic_id,
                display_name=f"ReleaseCopilot {environment_name} Budget Alerts",
                topic_name=sns_topic_name
                or f"releasecopilot-{normalized_env}-budget-alerts",
            )
            topic.add_to_resource_policy(
                iam.PolicyStatement(
                    sid="AllowBudgetsPublish",
                    actions=["SNS:Publish"],
                    effect=iam.Effect.ALLOW,
                    principals=[iam.ServicePrincipal("budgets.amazonaws.com")],
                    resources=[topic.topic_arn],
                )
            )
            self.topic = topic
            topic_arn = topic.topic_arn
            can_add_policy = True

        subscribers = [
            budgets.CfnBudget.SubscriberProperty(
                subscription_type="SNS",
                address=topic_arn,
            )
        ]

        for email in _sanitize_emails(email_recipients):
            subscribers.append(
                budgets.CfnBudget.SubscriberProperty(
                    subscription_type="EMAIL",
                    address=email,
                )
            )

        notifications = [
            budgets.CfnBudget.NotificationWithSubscribersProperty(
                notification=budgets.CfnBudget.NotificationProperty(
                    comparison_operator="GREATER_THAN",
                    notification_type="ACTUAL",
                    threshold=threshold,
                    threshold_type="PERCENTAGE",
                ),
                subscribers=list(subscribers),
            )
            for threshold in (50, 80, 100)
        ]

        budget_name = f"releasecopilot-{normalized_env}-monthly-cost"

        self.budget = budgets.CfnBudget(
            self,
            "MonthlyCostBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=budget_name,
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=budget_amount,
                    unit=currency,
                ),
                budget_type="COST",
                time_unit="MONTHLY",
            ),
            notifications_with_subscribers=notifications,
        )

        if can_add_policy:
            self.budget.node.add_dependency(self.topic)

    @property
    def sns_topic(self) -> sns.ITopic:
        """Expose the budget alert topic for stack integrations."""

        return self.topic


def _sanitize_emails(recipients: Iterable[str] | None) -> list[str]:
    if not recipients:
        return []
    sanitized: list[str] = []
    for email in recipients:
        trimmed = email.strip()
        if not trimmed:
            continue
        sanitized.append(trimmed)
    return sanitized
