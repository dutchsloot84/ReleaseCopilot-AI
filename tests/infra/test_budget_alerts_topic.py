"""Validate the BudgetAlerts topic resource policy."""

from aws_cdk import App, Stack
from aws_cdk.assertions import Template

from infra.cdk.constructs.budget_alerts import BudgetAlerts


def _synthesize_template() -> dict:
    app = App()
    stack = Stack(app, "TestStack")
    BudgetAlerts(stack, "TestBudgetAlerts", environment_name="Dev", budget_amount=100)
    template = Template.from_stack(stack).to_json()
    return template


def test_budget_alerts_topic_denies_non_tls_publish() -> None:
    template = _synthesize_template()

    deny_statements = []
    for resource in template["Resources"].values():
        if resource.get("Type") != "AWS::SNS::TopicPolicy":
            continue
        for statement in resource["Properties"]["PolicyDocument"]["Statement"]:
            if statement.get("Sid") == "DenyPublishWithoutTLS":
                deny_statements.append(statement)

    assert len(deny_statements) == 1

    deny = deny_statements[0]
    assert deny["Effect"] == "Deny"
    actions = deny["Action"]
    if isinstance(actions, str):
        actions = [actions]
    assert "sns:Publish" in actions
    assert deny["Condition"]["Bool"]["aws:SecureTransport"] == "false"
    assert deny["Principal"] in ("*", {"AWS": "*"})


def test_budget_alerts_topic_policy_has_single_tls_statement() -> None:
    template = _synthesize_template()

    statements = []
    for resource in template["Resources"].values():
        if resource.get("Type") != "AWS::SNS::TopicPolicy":
            continue
        statements.extend(resource["Properties"]["PolicyDocument"]["Statement"])

    sid_count = sum(
        1 for statement in statements if statement.get("Sid") == "DenyPublishWithoutTLS"
    )
    assert sid_count == 1
