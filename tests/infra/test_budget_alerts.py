"""Tests covering the budget alert wiring for the core stack."""

from __future__ import annotations

from pathlib import Path

from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from infra.cdk.core_stack import CoreStack

ACCOUNT = "123456789012"
REGION = "us-west-2"
ASSET_DIR = str(Path(__file__).resolve().parents[2] / "dist")


def _synth_template(**overrides) -> Template:
    app = App()
    stack = CoreStack(
        app,
        "TestBudgetStack",
        env=Environment(account=ACCOUNT, region=REGION),
        bucket_name=f"releasecopilot-artifacts-{ACCOUNT}",
        lambda_asset_path=ASSET_DIR,
        environment_name=overrides.pop("environment_name", "dev"),
        budget_amount=overrides.pop("budget_amount", 275.0),
        budget_currency=overrides.pop("budget_currency", "USD"),
        budget_email_recipients=overrides.pop("budget_email_recipients", ["alerts@example.com"]),
        **overrides,
    )
    return Template.from_stack(stack)


def test_budget_notifications_configured() -> None:
    template = _synth_template()

    template.resource_count_is("AWS::Budgets::Budget", 1)
    template.resource_count_is("AWS::SNS::Topic", 1)

    budget = next(iter(template.find_resources("AWS::Budgets::Budget").values()))

    assert budget["Properties"]["Budget"]["BudgetName"] == "releasecopilot-dev-monthly-cost"

    notifications = budget["Properties"]["NotificationsWithSubscribers"]
    assert len(notifications) == 3
    assert {entry["Notification"]["Threshold"] for entry in notifications} == {
        50,
        80,
        100,
    }

    template.has_resource_properties(
        "AWS::Budgets::Budget",
        Match.object_like(
            {
                "Budget": Match.object_like(
                    {
                        "BudgetLimit": {"Amount": 275.0, "Unit": "USD"},
                        "BudgetType": "COST",
                        "TimeUnit": "MONTHLY",
                    }
                ),
                "NotificationsWithSubscribers": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Notification": Match.object_like(
                                    {
                                        "ComparisonOperator": "GREATER_THAN",
                                        "NotificationType": "ACTUAL",
                                        "ThresholdType": "PERCENTAGE",
                                    }
                                ),
                                "Subscribers": Match.array_with(
                                    [
                                        Match.object_like({"SubscriptionType": "SNS"}),
                                        Match.object_like(
                                            {
                                                "SubscriptionType": "EMAIL",
                                                "Address": "alerts@example.com",
                                            }
                                        ),
                                    ]
                                ),
                            }
                        )
                    ]
                ),
            }
        ),
    )


def test_budget_topic_arn_output_present() -> None:
    template = _synth_template(
        budget_email_recipients=["finops@example.com"],
        environment_name="prod",
    )

    outputs = template.to_json().get("Outputs", {})
    assert "BudgetAlertsTopicArn" in outputs
    assert "Topic" in outputs["BudgetAlertsTopicArn"]["Value"]["Ref"]
