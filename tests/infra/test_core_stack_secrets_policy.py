"""Tests for secret wiring in the CoreStack."""

from __future__ import annotations

from aws_cdk import App
from aws_cdk.assertions import Template

from infra.cdk.core_stack import CoreStack


def _synth_stack() -> Template:
    app = App()
    stack = CoreStack(app, "TestStack", bucket_name="releasecopilot-artifacts-test")
    return Template.from_stack(stack)


def test_lambda_environment_exposes_secret_names() -> None:
    template = _synth_stack()

    functions = template.find_resources("AWS::Lambda::Function")

    def _environment(prefix: str) -> dict:
        for logical_id, resource in functions.items():
            if logical_id.startswith(prefix):
                return resource["Properties"]["Environment"]["Variables"]
        raise AssertionError(f"Lambda with prefix '{prefix}' not found")

    release_env = _environment("ReleaseCopilotLambda")
    webhook_env = _environment("JiraWebhookLambda")
    reconciliation_env = _environment("JiraReconciliationLambda")

    assert release_env["SECRET_JIRA"] == CoreStack.JIRA_SECRET_NAME
    assert release_env["SECRET_BITBUCKET"] == CoreStack.BITBUCKET_SECRET_NAME
    assert webhook_env["SECRET_WEBHOOK"] == CoreStack.WEBHOOK_SECRET_NAME
    assert reconciliation_env["SECRET_JIRA"] == CoreStack.JIRA_SECRET_NAME


def test_secret_policies_are_least_privilege() -> None:
    template = _synth_stack()

    policies = template.find_resources("AWS::IAM::Policy")
    secret_statements = []
    for policy in policies.values():
        statements = policy["Properties"]["PolicyDocument"]["Statement"]
        for statement in statements:
            actions = statement.get("Action")
            if not actions:
                continue
            if isinstance(actions, list):
                action_list = actions
            else:
                action_list = [actions]
            if not any(action.startswith("secretsmanager:") for action in action_list):
                continue
            secret_statements.append(statement)
            assert action_list == ["secretsmanager:GetSecretValue"]
            resources = statement.get("Resource")
            if isinstance(resources, list):
                for resource in resources:
                    assert resource != "*"
            else:
                assert resources != "*"

    assert len(secret_statements) == 4
