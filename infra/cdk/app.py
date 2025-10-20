#!/usr/bin/env python

"""CDK application entrypoint for the ReleaseCopilot infrastructure."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Optional, Tuple

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagSuppressions

from infra.cdk.core_stack import CoreStack


def _context(app: cdk.App, key: str, default: Any) -> Any:
    value = app.node.try_get_context(key)
    return default if value is None else value


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _csv_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        items = value
    else:
        text = str(value).strip()
        if not text:
            return []
        items = (item.strip() for item in text.split(","))
    return [item for item in items if item]


def _load_context(app: cdk.App) -> Dict[str, Any]:
    return {
        "env": str(_context(app, "env", "dev")),
        "region": str(_context(app, "region", "us-west-2")),
        "bucketBase": str(_context(app, "bucketBase", "releasecopilot-artifacts")),
        "account": _optional_str(_context(app, "account", None)),
        "jiraSecretArn": str(_context(app, "jiraSecretArn", "")),
        "bitbucketSecretArn": str(_context(app, "bitbucketSecretArn", "")),
        "scheduleEnabled": _to_bool(_context(app, "scheduleEnabled", False)),
        "scheduleCron": str(_context(app, "scheduleCron", "")),
        "lambdaAssetPath": str(_context(app, "lambdaAssetPath", "dist")),
        "lambdaHandler": str(_context(app, "lambdaHandler", "main.handler")),
        "lambdaTimeoutSec": int(_context(app, "lambdaTimeoutSec", 180)),
        "lambdaMemoryMb": int(_context(app, "lambdaMemoryMb", 512)),
        "jiraWebhookSecretArn": str(_context(app, "jiraWebhookSecretArn", "")),
        "jiraBaseUrl": str(_context(app, "jiraBaseUrl", "https://your-domain.atlassian.net")),
        "reconciliationCron": str(_context(app, "reconciliationCron", "")),
        "reconciliationFixVersions": str(_context(app, "reconciliationFixVersions", "")),
        "reconciliationJqlTemplate": str(
            _context(
                app,
                "reconciliationJqlTemplate",
                "fixVersion = '{fix_version}' ORDER BY key",
            )
        ),
        "reconciliationScheduleEnabled": _to_bool(
            _context(app, "reconciliationScheduleEnabled", True)
        ),
        "metricsNamespace": str(_context(app, "metricsNamespace", "ReleaseCopilot/JiraSync")),
        "budgetAmount": float(_context(app, "budgetAmount", 500)),
        "budgetCurrency": str(_context(app, "budgetCurrency", "USD")),
        "budgetEmailRecipients": _csv_list(_context(app, "budgetEmailRecipients", "")),
        "budgetSnsTopicName": str(_context(app, "budgetSnsTopicName", "")),
        "budgetExistingSnsTopicArn": str(_context(app, "budgetExistingSnsTopicArn", "")),
    }


def _aws_identity(region_hint: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    try:
        import boto3  # type: ignore
    except ImportError:  # pragma: no cover - boto3 optional for local synth
        return None, None

    try:
        session = boto3.session.Session(region_name=region_hint)
    except Exception:  # pragma: no cover - misconfigured boto3 session
        return None, region_hint

    resolved_region = session.region_name or region_hint

    try:
        sts = session.client("sts")
        identity = sts.get_caller_identity()
    except Exception:  # pragma: no cover - credentials missing/invalid
        return None, resolved_region

    return identity.get("Account"), resolved_region


def _resolve_environment(app: cdk.App, context: Dict[str, Any]) -> Tuple[Optional[str], str]:
    account = _optional_str(context.get("account"))
    region = _optional_str(context.get("region"))

    if not region:
        for candidate in (
            os.getenv("CDK_DEFAULT_REGION"),
            os.getenv("AWS_REGION"),
            os.getenv("AWS_DEFAULT_REGION"),
        ):
            region = _optional_str(candidate)
            if region:
                break

    if not account:
        account_from_context = _optional_str(app.node.try_get_context("account"))
        if account_from_context:
            account = account_from_context

    boto_account, boto_region = _aws_identity(region)
    if not region and boto_region:
        region = boto_region
    if not account and boto_account:
        account = boto_account

    if not account:
        for candidate in (
            os.getenv("CDK_DEFAULT_ACCOUNT"),
            os.getenv("AWS_ACCOUNT_ID"),
            os.getenv("ACCOUNT_ID"),
        ):
            account = _optional_str(candidate)
            if account:
                break

    if not region:
        region = "us-west-2"

    return account, region


app = cdk.App()
cdk.Aspects.of(app).add(AwsSolutionsChecks())
context = _load_context(app)

account_id, region = _resolve_environment(app, context)

bucket_suffix = f"-{account_id}" if account_id else ""
bucket_name = f"{context['bucketBase']}{bucket_suffix}"

environment = cdk.Environment(account=account_id, region=region)

core_stack = CoreStack(
    app,
    f"ReleaseCopilot-{context['env']}-Core",
    env=environment,
    bucket_name=bucket_name,
    jira_secret_arn=context["jiraSecretArn"] or None,
    bitbucket_secret_arn=context["bitbucketSecretArn"] or None,
    lambda_asset_path=context["lambdaAssetPath"],
    lambda_handler=context["lambdaHandler"],
    lambda_timeout_sec=context["lambdaTimeoutSec"],
    lambda_memory_mb=context["lambdaMemoryMb"],
    schedule_enabled=context["scheduleEnabled"],
    schedule_cron=context["scheduleCron"],
    jira_webhook_secret_arn=context["jiraWebhookSecretArn"] or None,
    reconciliation_schedule_expression=context["reconciliationCron"] or None,
    enable_reconciliation_schedule=context["reconciliationScheduleEnabled"],
    reconciliation_fix_versions=context["reconciliationFixVersions"] or None,
    reconciliation_jql_template=context["reconciliationJqlTemplate"] or None,
    jira_base_url=context["jiraBaseUrl"] or None,
    metrics_namespace=context["metricsNamespace"] or None,
    environment_name=context["env"],
    budget_amount=context["budgetAmount"],
    budget_currency=context["budgetCurrency"],
    budget_email_recipients=context["budgetEmailRecipients"],
    budget_sns_topic_name=context["budgetSnsTopicName"] or None,
    budget_existing_sns_topic_arn=context["budgetExistingSnsTopicArn"] or None,
)

NagSuppressions.add_stack_suppressions(
    core_stack,
    suppressions=[
        {
            "id": "AwsSolutions-S1",
            "reason": (
                "Artifacts bucket access is audited through CloudTrail and used only for short-lived deployment assets."
            ),
        },
        {
            "id": "AwsSolutions-SMG4",
            "reason": (
                "OAuth credentials are managed through Atlassian admin flows, so automated rotation is not currently possible."
            ),
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": (
                "Scoped wildcards are required for DynamoDB secondary indexes and the ReleaseCopilot artifacts prefix."
            ),
        },
        {
            "id": "AwsSolutions-L1",
            "reason": (
                "Python 3.11 remains the validated runtime for the packaged dependencies and stays within AWS support windows."
            ),
        },
        {
            "id": "AwsSolutions-IAM4",
            "reason": (
                "Service-linked managed policies are retained for Lambda and API Gateway to preserve AWS operational baselines."
            ),
        },
        {
            "id": "AwsSolutions-APIG2",
            "reason": (
                "The Jira webhook payload is validated inside the Lambda handler using a shared secret, making request validation redundant."
            ),
        },
        {
            "id": "AwsSolutions-APIG3",
            "reason": (
                "A WAF is deferred while the webhook remains protected by shared-secret authentication and rate limiting upstream."
            ),
        },
        {
            "id": "AwsSolutions-APIG4",
            "reason": (
                "Shared-secret authentication performed by the Lambda handler intentionally replaces API Gateway authorizers."
            ),
        },
        {
            "id": "AwsSolutions-COG4",
            "reason": (
                "Atlassian cannot integrate with Cognito authorizers; the webhook enforces authentication through the shared secret."
            ),
        },
    ],
)

NagSuppressions.add_stack_suppressions(
    core_stack,
    suppressions=[
        {
            "id": "AwsSolutions-S1",
            "reason": (
                "Artifacts bucket access is audited through CloudTrail and used only for short-lived deployment assets."
            ),
        },
        {
            "id": "AwsSolutions-SMG4",
            "reason": (
                "OAuth credentials are managed through Atlassian admin flows, so automated rotation is not currently possible."
            ),
        },
        {
            "id": "AwsSolutions-IAM5",
            "reason": (
                "Scoped wildcards are required for DynamoDB secondary indexes and the ReleaseCopilot artifacts prefix."
            ),
        },
        {
            "id": "AwsSolutions-L1",
            "reason": (
                "Python 3.11 remains the validated runtime for the packaged dependencies and stays within AWS support windows."
            ),
        },
        {
            "id": "AwsSolutions-IAM4",
            "reason": (
                "Service-linked managed policies are retained for Lambda and API Gateway to preserve AWS operational baselines."
            ),
        },
        {
            "id": "AwsSolutions-APIG2",
            "reason": (
                "The Jira webhook payload is validated inside the Lambda handler using a shared secret, making request validation redundant."
            ),
        },
        {
            "id": "AwsSolutions-APIG3",
            "reason": (
                "A WAF is deferred while the webhook remains protected by shared-secret authentication and rate limiting upstream."
            ),
        },
        {
            "id": "AwsSolutions-APIG4",
            "reason": (
                "Shared-secret authentication performed by the Lambda handler intentionally replaces API Gateway authorizers."
            ),
        },
        {
            "id": "AwsSolutions-COG4",
            "reason": (
                "Atlassian cannot integrate with Cognito authorizers; the webhook enforces authentication through the shared secret."
            ),
        },
    ],
)

app.synth()
