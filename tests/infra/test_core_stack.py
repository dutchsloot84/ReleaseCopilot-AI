"""Unit tests validating the CDK core stack resources."""

from __future__ import annotations

from pathlib import Path

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from infra.cdk.core_stack import CoreStack

ACCOUNT = "123456789012"
REGION = "us-west-2"
ASSET_DIR = str(Path(__file__).resolve().parents[2] / "dist")


def _synth_template(*, app_context: dict[str, str] | None = None, **overrides) -> Template:
    app = App(context=app_context or {})
    stack = CoreStack(
        app,
        "TestCoreStack",
        env=Environment(account=ACCOUNT, region=REGION),
        bucket_name=f"releasecopilot-artifacts-{ACCOUNT}",
        lambda_asset_path=ASSET_DIR,
        **overrides,
    )
    return Template.from_stack(stack)


def _create_stack(*, app_context: dict[str, str] | None = None, **overrides) -> CoreStack:
    app = App(context=app_context or {})
    return CoreStack(
        app,
        "TestCoreStack",
        env=Environment(account=ACCOUNT, region=REGION),
        bucket_name=f"releasecopilot-artifacts-{ACCOUNT}",
        lambda_asset_path=ASSET_DIR,
        **overrides,
    )


def test_bucket_encryption_and_versioning() -> None:
    template = _synth_template()
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "VersioningConfiguration": {"Status": "Enabled"},
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": Match.array_with(
                    [
                        Match.object_like(
                            {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                        )
                    ]
                )
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "OwnershipControls": {
                "Rules": Match.array_with(
                    [Match.object_like({"ObjectOwnership": "BucketOwnerEnforced"})]
                )
            },
        },
    )


def test_bucket_lifecycle_rules() -> None:
    template = _synth_template()
    bucket = next(iter(template.find_resources("AWS::S3::Bucket").values()))
    lifecycle_rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]

    rules_by_id = {rule["Id"]: rule for rule in lifecycle_rules}

    assert {
        "ArtifactsJsonLifecycle",
        "ArtifactsExcelLifecycle",
        "TempDataExpiration",
        "LogsLifecycle",
    }.issubset(rules_by_id)

    json_rule = rules_by_id["ArtifactsJsonLifecycle"]
    assert json_rule["Prefix"] == "releasecopilot/artifacts/json/"
    assert json_rule["Transitions"] == [
        {"StorageClass": "STANDARD_IA", "TransitionInDays": 45},
        {"StorageClass": "DEEP_ARCHIVE", "TransitionInDays": 365},
    ]
    assert json_rule["NoncurrentVersionTransitions"] == [
        {"StorageClass": "DEEP_ARCHIVE", "TransitionInDays": 365}
    ]

    excel_rule = rules_by_id["ArtifactsExcelLifecycle"]
    assert excel_rule["Prefix"] == "releasecopilot/artifacts/excel/"
    assert excel_rule["Transitions"] == [
        {"StorageClass": "STANDARD_IA", "TransitionInDays": 45},
        {"StorageClass": "DEEP_ARCHIVE", "TransitionInDays": 365},
    ]
    assert excel_rule["NoncurrentVersionTransitions"] == [
        {"StorageClass": "DEEP_ARCHIVE", "TransitionInDays": 365}
    ]

    temp_rule = rules_by_id["TempDataExpiration"]
    assert temp_rule["Prefix"] == "releasecopilot/temp_data/"
    assert temp_rule["ExpirationInDays"] == 10

    logs_rule = rules_by_id["LogsLifecycle"]
    assert logs_rule["Prefix"] == "releasecopilot/logs/"
    assert logs_rule["Transitions"] == [{"StorageClass": "STANDARD_IA", "TransitionInDays": 30}]
    assert logs_rule["ExpirationInDays"] == 120


def test_bucket_policy_enforces_security() -> None:
    template = _synth_template()
    policies = template.find_resources("AWS::S3::BucketPolicy")
    assert policies, "Expected bucket policy to be synthesized"
    policy = next(iter(policies.values()))
    statements = policy["Properties"]["PolicyDocument"]["Statement"]

    tls_statement = next(
        stmt
        for stmt in statements
        if stmt.get("Condition") == {"Bool": {"aws:SecureTransport": "false"}}
    )
    assert tls_statement["Effect"] == "Deny"
    tls_actions = tls_statement["Action"]
    if isinstance(tls_actions, list):
        assert set(tls_actions) == {"s3:*"}
    else:
        assert tls_actions == "s3:*"

    encryption_statement = next(
        stmt for stmt in statements if stmt.get("Sid") == "DenyUnencryptedUploads"
    )
    assert encryption_statement["Effect"] == "Deny"
    encryption_actions = encryption_statement["Action"]
    if isinstance(encryption_actions, list):
        assert set(encryption_actions) == {"s3:PutObject"}
    else:
        assert encryption_actions == "s3:PutObject"
    expected_condition = {
        "StringNotEquals": {"s3:x-amz-server-side-encryption": "AES256"},
        "Null": {"s3:x-amz-server-side-encryption": True},
    }
    observed_condition = encryption_statement["Condition"]
    # CDK may render the Null condition as a string or boolean literal.
    if observed_condition.get("Null", {}).get("s3:x-amz-server-side-encryption") == "true":
        observed_condition = {
            **observed_condition,
            "Null": {"s3:x-amz-server-side-encryption": True},
        }
    assert observed_condition == expected_condition


def test_iam_policy_statements() -> None:
    template = _synth_template()
    policies = template.find_resources("AWS::IAM::Policy")
    policy = next(policy for name, policy in policies.items() if "LambdaExecutionPolicy" in name)
    statements = policy["Properties"]["PolicyDocument"]["Statement"]

    assert {stmt["Sid"] for stmt in statements} == {
        "AllowS3ObjectAccess",
        "AllowS3ListArtifactsPrefix",
        "AllowSecretRetrieval",
        "AllowLambdaLogging",
    }

    object_statement = next(stmt for stmt in statements if stmt["Sid"] == "AllowS3ObjectAccess")
    assert set(object_statement["Action"]) == {"s3:GetObject", "s3:PutObject"}
    object_resources = object_statement["Resource"]
    assert isinstance(object_resources, list)
    for resource in object_resources:
        assert resource["Fn::Join"][1][1].startswith("/releasecopilot/")

    list_statement = next(
        stmt for stmt in statements if stmt["Sid"] == "AllowS3ListArtifactsPrefix"
    )
    assert list_statement["Action"] == "s3:ListBucket"
    assert list_statement["Condition"] == {
        "StringLike": {
            "s3:prefix": [
                "releasecopilot/artifacts/json/",
                "releasecopilot/artifacts/json/*",
                "releasecopilot/artifacts/excel/",
                "releasecopilot/artifacts/excel/*",
                "releasecopilot/temp_data/",
                "releasecopilot/temp_data/*",
            ]
        }
    }

    secrets_statement = next(stmt for stmt in statements if stmt["Sid"] == "AllowSecretRetrieval")
    assert secrets_statement["Action"] == "secretsmanager:GetSecretValue"
    resources = secrets_statement["Resource"]
    assert isinstance(resources, list)
    assert len(resources) == 3
    assert "*" not in resources

    logs_statement = next(stmt for stmt in statements if stmt["Sid"] == "AllowLambdaLogging")
    assert set(logs_statement["Action"]) == {
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    }
    resources = logs_statement["Resource"]
    assert isinstance(resources, list)
    assert len(resources) == 3

    log_group_ids = set(template.find_resources("AWS::Logs::LogGroup").keys())
    assert all(isinstance(resource, dict) and "Fn::GetAtt" in resource for resource in resources)

    statement_log_group_ids = {resource["Fn::GetAtt"][0] for resource in resources}

    assert statement_log_group_ids.issubset(log_group_ids)
    assert all(resource["Fn::GetAtt"][1] == "Arn" for resource in resources)


def test_managed_policies_scope_access() -> None:
    template = _synth_template()
    policies = template.find_resources("AWS::IAM::ManagedPolicy")
    assert len(policies) >= 2

    reader_policy = next(
        policy
        for policy in policies.values()
        if policy["Properties"]["ManagedPolicyName"].endswith("ArtifactsRead")
    )
    writer_policy = next(
        policy
        for policy in policies.values()
        if policy["Properties"]["ManagedPolicyName"].endswith("ArtifactsWrite")
    )

    reader_statements = reader_policy["Properties"]["PolicyDocument"]["Statement"]
    assert {stmt["Sid"] for stmt in reader_statements} == {
        "AllowArtifactReads",
        "AllowArtifactList",
    }
    read_resource_statement = next(
        stmt for stmt in reader_statements if stmt["Sid"] == "AllowArtifactReads"
    )
    read_suffixes = {resource["Fn::Join"][1][1] for resource in read_resource_statement["Resource"]}
    assert read_suffixes == {
        "/releasecopilot/artifacts/json/*",
        "/releasecopilot/artifacts/excel/*",
    }

    writer_statements = writer_policy["Properties"]["PolicyDocument"]["Statement"]
    assert {stmt["Sid"] for stmt in writer_statements} == {
        "AllowArtifactWrites",
        "AllowArtifactWriteList",
    }
    write_resource_statement = next(
        stmt for stmt in writer_statements if stmt["Sid"] == "AllowArtifactWrites"
    )
    write_suffixes = {
        resource["Fn::Join"][1][1] for resource in write_resource_statement["Resource"]
    }
    assert write_suffixes == {
        "/releasecopilot/artifacts/json/*",
        "/releasecopilot/artifacts/excel/*",
        "/releasecopilot/temp_data/*",
    }


def test_lambda_environment_and_log_groups() -> None:
    template = _synth_template()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        Match.object_like(
            {
                "Runtime": "python3.11",
                "Environment": {
                    "Variables": Match.object_like(
                        {
                            "RC_S3_BUCKET": Match.any_value(),
                            "RC_S3_PREFIX": "releasecopilot",
                            "RC_USE_AWS_SECRETS_MANAGER": "true",
                        }
                    )
                },
            }
        ),
    )

    log_groups = template.find_resources("AWS::Logs::LogGroup")
    assert len(log_groups) >= 3
    for log_group in log_groups.values():
        assert log_group["Properties"].get("RetentionInDays") == 30

    assert not template.find_resources("Custom::LogRetention")


def test_lambda_asset_paths_are_stable() -> None:
    project_root = Path(__file__).resolve().parents[2]
    webhook_path = project_root / "services" / "jira_sync_webhook"
    reconciliation_path = project_root / "services" / "jira_reconciliation_job"

    assert webhook_path.is_dir()
    assert reconciliation_path.is_dir()


def test_stack_raises_when_asset_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = Path(__file__).resolve().parents[2]
    webhook_path = project_root / "services" / "jira_sync_webhook"
    reconciliation_path = project_root / "services" / "jira_reconciliation_job"

    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if self in {webhook_path, reconciliation_path}:
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    with pytest.raises(FileNotFoundError):
        _create_stack()


def test_lambda_alarms_created() -> None:
    template = _synth_template()
    template.resource_count_is("AWS::CloudWatch::Alarm", 3)


def test_reconciliation_dlq_alarm_configuration() -> None:
    template = _synth_template()
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        Match.object_like(
            {
                "MetricName": "ApproximateNumberOfMessagesVisible",
                "Namespace": "AWS/SQS",
                "Threshold": 1,
                "Dimensions": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Name": "QueueName",
                            }
                        )
                    ]
                ),
            }
        ),
    )


def test_sns_topic_created_when_alarm_email_provided() -> None:
    template = _synth_template(app_context={"alarmEmail": "ops@example.com"})
    topics = template.find_resources("AWS::SNS::Topic")
    assert len(topics) == 2
    assert any("BudgetAlerts" in name for name in topics)
    template.resource_count_is("AWS::SNS::Subscription", 1)
    template.has_resource_properties(
        "AWS::SNS::Subscription",
        {"Endpoint": "ops@example.com"},
    )


def test_stack_outputs_present() -> None:
    template = _synth_template()
    outputs = template.to_json()["Outputs"]
    assert "ArtifactsBucketName" in outputs
    assert "LambdaArn" in outputs
    assert "JiraReconciliationLambdaName" in outputs
    assert "JiraReconciliationDlqArn" in outputs
    assert "JiraReconciliationDlqUrl" in outputs


def test_eventbridge_rule_targets_lambda_when_enabled() -> None:
    template = _synth_template(
        schedule_enabled=True,
        schedule_cron="cron(0 12 * * ? *)",
    )

    rules = template.find_resources("AWS::Events::Rule")
    assert len(rules) == 2

    release_rule = next(
        rule
        for rule in rules.values()
        if rule["Properties"]["Targets"][0]["Arn"]["Fn::GetAtt"][0].startswith(
            "ReleaseCopilotLambda"
        )
    )
    release_properties = release_rule["Properties"]
    assert release_properties["ScheduleExpression"] == "cron(0 12 * * ? *)"

    reconciliation_rule = next(
        rule
        for rule in rules.values()
        if rule["Properties"]["Targets"][0]["Arn"]["Fn::GetAtt"][0].startswith(
            "JiraReconciliationLambda"
        )
    )
    reconciliation_properties = reconciliation_rule["Properties"]
    assert reconciliation_properties["ScheduleExpression"] == "cron(15 7 * * ? *)"
    assert reconciliation_properties["Targets"][0]["DeadLetterConfig"]


def test_eventbridge_rule_absent_when_schedule_disabled() -> None:
    template = _synth_template(schedule_enabled=False)

    rules = template.find_resources("AWS::Events::Rule")
    assert len(rules) == 1
    target = rules[next(iter(rules))]["Properties"]["Targets"][0]
    assert target["Arn"]["Fn::GetAtt"][0].startswith("JiraReconciliationLambda")


def test_reconciliation_lambda_and_queue_created() -> None:
    template = _synth_template()

    template.has_resource_properties(
        "AWS::Lambda::Function",
        Match.object_like(
            {
                "Handler": "handler.handler",
                "Runtime": "python3.11",
                "Environment": {
                    "Variables": Match.object_like(
                        {
                            "JIRA_BASE_URL": Match.any_value(),
                            "JIRA_SECRET_ARN": Match.any_value(),
                            "METRICS_NAMESPACE": "ReleaseCopilot/JiraSync",
                        }
                    )
                },
            }
        ),
    )

    template.has_resource_properties(
        "AWS::SQS::Queue",
        {
            "MessageRetentionPeriod": 1209600,
        },
    )
