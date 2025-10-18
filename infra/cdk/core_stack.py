"""CDK stack defining the ReleaseCopilot core infrastructure."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_apigateway as apigateway,
)
from aws_cdk import (
    aws_cloudwatch as cw,
)
from aws_cdk import (
    aws_cloudwatch_actions as actions,
)
from aws_cdk import (
    aws_dynamodb as dynamodb,
)
from aws_cdk import (
    aws_events as events,
)
from aws_cdk import (
    aws_events_targets as targets,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_logs as logs,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)
from aws_cdk import (
    aws_sns as sns,
)
from aws_cdk import (
    aws_sns_subscriptions as subs,
)
from aws_cdk import (
    aws_sqs as sqs,
)
from constructs import Construct

from .constructs import BudgetAlerts, SecretAccess


class CoreStack(Stack):
    """Provision the ReleaseCopilot storage, secrets, and execution runtime."""

    RC_S3_PREFIX = "releasecopilot"
    ARTIFACTS_PREFIX = f"{RC_S3_PREFIX}/artifacts"
    ARTIFACTS_JSON_PREFIX = f"{ARTIFACTS_PREFIX}/json"
    ARTIFACTS_EXCEL_PREFIX = f"{ARTIFACTS_PREFIX}/excel"
    TEMP_DATA_PREFIX = f"{RC_S3_PREFIX}/temp_data"
    LOGS_PREFIX = f"{RC_S3_PREFIX}/logs"

    TEMP_DATA_EXPIRATION_DAYS = 10
    LOGS_IA_AFTER_DAYS = 30
    LOGS_EXPIRATION_DAYS = 120
    ARTIFACTS_IA_AFTER_DAYS = 45
    ARTIFACTS_GLACIER_AFTER_DAYS = 365
    ARTIFACTS_NONCURRENT_VERSIONS = 5
    JIRA_SECRET_NAME = "releasecopilot/jira/oauth"
    BITBUCKET_SECRET_NAME = "releasecopilot/bitbucket/token"
    WEBHOOK_SECRET_NAME = "releasecopilot/jira/webhook_secret"

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        bucket_name: str,
        jira_secret_arn: Optional[str] = None,
        bitbucket_secret_arn: Optional[str] = None,
        lambda_asset_path: str = "dist",
        lambda_handler: str = "main.handler",
        lambda_timeout_sec: int = 180,
        lambda_memory_mb: int = 512,
        schedule_enabled: bool = False,
        schedule_cron: str | None = None,
        jira_webhook_secret_arn: Optional[str] = None,
        reconciliation_schedule_expression: str | None = None,
        enable_reconciliation_schedule: bool = True,
        reconciliation_fix_versions: Optional[str] = None,
        reconciliation_jql_template: Optional[str] = None,
        jira_base_url: Optional[str] = None,
        metrics_namespace: Optional[str] = None,
        environment_name: str = "dev",
        budget_amount: float = 100.0,
        budget_currency: str = "USD",
        budget_email_recipients: Sequence[str] | None = None,
        budget_sns_topic_name: Optional[str] = None,
        budget_existing_sns_topic_arn: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment_name = environment_name

        asset_path = Path(lambda_asset_path).expanduser().resolve()
        project_root = Path(__file__).resolve().parents[2]
        webhook_asset_path = project_root / "services" / "jira_sync_webhook"
        reconciliation_asset_path = project_root / "services" / "jira_reconciliation_job"

        if not webhook_asset_path.exists():
            raise FileNotFoundError(
                f"Jira webhook Lambda asset directory is missing: {webhook_asset_path}"
            )
        if not reconciliation_asset_path.exists():
            raise FileNotFoundError(
                "Jira reconciliation Lambda asset directory is missing: "
                f"{reconciliation_asset_path}"
            )

        self.bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name=bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
        )

        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyInsecureTransport",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:*"],
                resources=[
                    self.bucket.bucket_arn,
                    self.bucket.arn_for_objects("*"),
                ],
                conditions={"Bool": {"aws:SecureTransport": "false"}},
            )
        )

        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="DenyUnencryptedUploads",
                effect=iam.Effect.DENY,
                principals=[iam.AnyPrincipal()],
                actions=["s3:PutObject"],
                resources=[self.bucket.arn_for_objects("*")],
                conditions={
                    "StringNotEquals": {"s3:x-amz-server-side-encryption": "AES256"},
                    "Null": {"s3:x-amz-server-side-encryption": "true"},
                },
            )
        )

        self.bucket.add_lifecycle_rule(
            id="ArtifactsJsonLifecycle",
            prefix=f"{self.ARTIFACTS_JSON_PREFIX}/",
            transitions=[
                s3.Transition(
                    storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                    transition_after=Duration.days(self.ARTIFACTS_IA_AFTER_DAYS),
                ),
                s3.Transition(
                    storage_class=s3.StorageClass.DEEP_ARCHIVE,
                    transition_after=Duration.days(self.ARTIFACTS_GLACIER_AFTER_DAYS),
                ),
            ],
            noncurrent_version_transitions=[
                s3.NoncurrentVersionTransition(
                    storage_class=s3.StorageClass.DEEP_ARCHIVE,
                    transition_after=Duration.days(self.ARTIFACTS_GLACIER_AFTER_DAYS),
                )
            ],
            noncurrent_versions_to_retain=self.ARTIFACTS_NONCURRENT_VERSIONS,
        )

        self.bucket.add_lifecycle_rule(
            id="ArtifactsExcelLifecycle",
            prefix=f"{self.ARTIFACTS_EXCEL_PREFIX}/",
            transitions=[
                s3.Transition(
                    storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                    transition_after=Duration.days(self.ARTIFACTS_IA_AFTER_DAYS),
                ),
                s3.Transition(
                    storage_class=s3.StorageClass.DEEP_ARCHIVE,
                    transition_after=Duration.days(self.ARTIFACTS_GLACIER_AFTER_DAYS),
                ),
            ],
            noncurrent_version_transitions=[
                s3.NoncurrentVersionTransition(
                    storage_class=s3.StorageClass.DEEP_ARCHIVE,
                    transition_after=Duration.days(self.ARTIFACTS_GLACIER_AFTER_DAYS),
                )
            ],
            noncurrent_versions_to_retain=self.ARTIFACTS_NONCURRENT_VERSIONS,
        )

        self.bucket.add_lifecycle_rule(
            id="TempDataExpiration",
            prefix=f"{self.TEMP_DATA_PREFIX}/",
            expiration=Duration.days(self.TEMP_DATA_EXPIRATION_DAYS),
        )

        self.bucket.add_lifecycle_rule(
            id="LogsLifecycle",
            prefix=f"{self.LOGS_PREFIX}/",
            transitions=[
                s3.Transition(
                    storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                    transition_after=Duration.days(self.LOGS_IA_AFTER_DAYS),
                )
            ],
            expiration=Duration.days(self.LOGS_EXPIRATION_DAYS),
        )

        self.jira_secret = self._resolve_secret(
            "JiraSecret",
            provided_arn=jira_secret_arn,
            description="Placeholder Jira OAuth secret for ReleaseCopilot",
            secret_name=self.JIRA_SECRET_NAME,
        )
        self.bitbucket_secret = self._resolve_secret(
            "BitbucketSecret",
            provided_arn=bitbucket_secret_arn,
            description="Placeholder Bitbucket OAuth secret for ReleaseCopilot",
            secret_name=self.BITBUCKET_SECRET_NAME,
        )

        self.secret_access = SecretAccess(self, "SecretAccess")

        self.budget_alerts = BudgetAlerts(
            self,
            "BudgetAlerts",
            environment_name=environment_name,
            budget_amount=budget_amount,
            currency=budget_currency,
            email_recipients=budget_email_recipients,
            sns_topic_name=budget_sns_topic_name,
            existing_topic_arn=budget_existing_sns_topic_arn,
        )

        if budget_existing_sns_topic_arn:
            budget_topic_arn = budget_existing_sns_topic_arn
        else:
            budget_topic_arn = self.budget_alerts.sns_topic.topic_arn

        CfnOutput(
            self,
            "BudgetAlertsTopicArn",
            value=budget_topic_arn,
            description="SNS topic receiving AWS Budgets cost alerts.",
        )

        self.execution_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Least-privilege execution role for ReleaseCopilot Lambda",
        )

        environment = {
            "RC_S3_BUCKET": self.bucket.bucket_name,
            "RC_S3_PREFIX": self.RC_S3_PREFIX,
            "RC_USE_AWS_SECRETS_MANAGER": "true",
        }

        clamped_timeout = max(180, min(lambda_timeout_sec, 300))
        clamped_memory = max(512, min(lambda_memory_mb, 1024))

        self.release_lambda_log_group = logs.LogGroup(
            self,
            "ReleaseCopilotLambdaLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.lambda_function = _lambda.Function(
            self,
            "ReleaseCopilotLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler=lambda_handler,
            code=_lambda.Code.from_asset(str(asset_path)),
            timeout=Duration.seconds(clamped_timeout),
            memory_size=clamped_memory,
            role=self.execution_role,
            environment=environment,
            log_group=self.release_lambda_log_group,
        )

        self.jira_table = dynamodb.Table(
            self,
            "JiraIssuesTable",
            partition_key=dynamodb.Attribute(name="issue_key", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="updated_at", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
        )

        cfn_table = self.jira_table.node.default_child
        if isinstance(cfn_table, dynamodb.CfnTable):
            cfn_table.point_in_time_recovery_specification = (
                dynamodb.CfnTable.PointInTimeRecoverySpecificationProperty(
                    point_in_time_recovery_enabled=True
                )
            )

        self.jira_table.add_global_secondary_index(
            index_name="FixVersionIndex",
            partition_key=dynamodb.Attribute(
                name="fix_version", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="updated_at", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )
        self.jira_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="updated_at", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )
        self.jira_table.add_global_secondary_index(
            index_name="AssigneeIndex",
            partition_key=dynamodb.Attribute(name="assignee", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="updated_at", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        self.lambda_function.add_environment("JIRA_TABLE_NAME", self.jira_table.table_name)
        self.jira_table.grant_read_data(self.lambda_function)

        webhook_secret = self._resolve_secret(
            "JiraWebhookSecret",
            provided_arn=jira_webhook_secret_arn,
            description="Shared secret used to authenticate Jira webhook deliveries",
            secret_name=self.WEBHOOK_SECRET_NAME,
        )

        webhook_environment = {
            "TABLE_NAME": self.jira_table.table_name,
            "LOG_LEVEL": "INFO",
            "RC_DDB_MAX_ATTEMPTS": "5",
        }
        if webhook_secret:
            webhook_environment["WEBHOOK_SECRET_ARN"] = webhook_secret.secret_arn

        self.webhook_lambda_log_group = logs.LogGroup(
            self,
            "JiraWebhookLambdaLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.webhook_lambda = _lambda.Function(
            self,
            "JiraWebhookLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset(str(webhook_asset_path)),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment=webhook_environment,
            log_group=self.webhook_lambda_log_group,
        )

        self.jira_table.grant_read_write_data(self.webhook_lambda)

        reconciliation_environment = {
            "TABLE_NAME": self.jira_table.table_name,
            "JIRA_BASE_URL": (jira_base_url or "https://your-domain.atlassian.net"),
            "RC_DDB_MAX_ATTEMPTS": "5",
            "RC_DDB_BASE_DELAY": "0.5",
            "METRICS_NAMESPACE": metrics_namespace or "ReleaseCopilot/JiraSync",
            "JIRA_SECRET_ARN": self.jira_secret.secret_arn,
        }
        if reconciliation_fix_versions:
            reconciliation_environment["FIX_VERSIONS"] = reconciliation_fix_versions
        if reconciliation_jql_template:
            reconciliation_environment["JQL_TEMPLATE"] = reconciliation_jql_template

        self.reconciliation_dlq = sqs.Queue(
            self,
            "JiraReconciliationDLQ",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            enforce_ssl=True,
        )

        self.reconciliation_lambda_log_group = logs.LogGroup(
            self,
            "JiraReconciliationLambdaLogGroup",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.reconciliation_lambda = _lambda.Function(
            self,
            "JiraReconciliationLambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset(str(reconciliation_asset_path)),
            timeout=Duration.seconds(300),
            memory_size=512,
            environment=reconciliation_environment,
            log_group=self.reconciliation_lambda_log_group,
            dead_letter_queue=self.reconciliation_dlq,
            dead_letter_queue_enabled=True,
            max_event_age=Duration.hours(6),
            retry_attempts=2,
        )

        self.secret_access.grant(
            environment_key="SECRET_JIRA",
            secret_name=self.JIRA_SECRET_NAME,
            secret=self.jira_secret,
            functions=[self.lambda_function],
        )
        self.secret_access.grant(
            environment_key="SECRET_JIRA",
            secret_name=self.JIRA_SECRET_NAME,
            secret=self.jira_secret,
            functions=[self.reconciliation_lambda],
        )
        self.secret_access.grant(
            environment_key="SECRET_BITBUCKET",
            secret_name=self.BITBUCKET_SECRET_NAME,
            secret=self.bitbucket_secret,
            functions=[self.lambda_function],
            attach_to_role=False,
        )
        if webhook_secret:
            self.secret_access.grant(
                environment_key="SECRET_WEBHOOK",
                secret_name=self.WEBHOOK_SECRET_NAME,
                secret=webhook_secret,
                functions=[self.webhook_lambda],
            )

        self._attach_policies()

        self.jira_table.grant_read_write_data(self.reconciliation_lambda)

        self.webhook_api_access_logs = logs.LogGroup(
            self,
            "JiraWebhookApiAccessLogs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.webhook_api = apigateway.RestApi(
            self,
            "JiraWebhookApi",
            rest_api_name="ReleaseCopilotJiraWebhook",
            deploy_options=apigateway.StageOptions(
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=False,
                metrics_enabled=True,
                access_log_destination=apigateway.LogGroupLogDestination(
                    self.webhook_api_access_logs
                ),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
            ),
        )

        jira_resource = self.webhook_api.root.add_resource("jira")
        webhook_resource = jira_resource.add_resource("webhook")
        webhook_integration = apigateway.LambdaIntegration(self.webhook_lambda)
        webhook_resource.add_method("POST", webhook_integration)

        self._alarm_action = self._configure_alarm_action()
        self._add_lambda_alarms()
        self._add_reconciliation_dlq_alarm()
        self._add_schedule(schedule_enabled=schedule_enabled, schedule_cron=schedule_cron)

        self._add_reconciliation_schedule(
            enable_schedule=enable_reconciliation_schedule,
            schedule_expression=reconciliation_schedule_expression,
        )

        CfnOutput(self, "ArtifactsBucketName", value=self.bucket.bucket_name)
        CfnOutput(
            self,
            "ArtifactsReadPolicyArn",
            value=self.artifact_reader_policy.managed_policy_arn,
            description="IAM managed policy granting read-only access to release artifacts.",
        )
        CfnOutput(
            self,
            "ArtifactsWritePolicyArn",
            value=self.artifact_writer_policy.managed_policy_arn,
            description="IAM managed policy granting write access to release artifacts and temp data.",
        )
        CfnOutput(self, "LambdaName", value=self.lambda_function.function_name)
        CfnOutput(self, "LambdaArn", value=self.lambda_function.function_arn)
        CfnOutput(self, "JiraTableName", value=self.jira_table.table_name)
        CfnOutput(self, "JiraTableArn", value=self.jira_table.table_arn)
        CfnOutput(self, "JiraWebhookUrl", value=self.webhook_api.url)
        CfnOutput(
            self,
            "JiraReconciliationLambdaName",
            value=self.reconciliation_lambda.function_name,
        )
        CfnOutput(self, "JiraReconciliationDlqArn", value=self.reconciliation_dlq.queue_arn)
        CfnOutput(self, "JiraReconciliationDlqUrl", value=self.reconciliation_dlq.queue_url)

    def _attach_policies(self) -> None:
        log_group_arns = [
            self.release_lambda_log_group.log_group_arn,
            self.webhook_lambda_log_group.log_group_arn,
            self.reconciliation_lambda_log_group.log_group_arn,
        ]
        secret_arns = sorted({grant.secret.secret_arn for grant in self.secret_access.grants})

        statements: list[iam.PolicyStatement] = []
        if secret_arns:
            statements.append(
                iam.PolicyStatement(
                    sid="AllowSecretRetrieval",
                    actions=["secretsmanager:GetSecretValue"],
                    resources=secret_arns,
                )
            )

        artifact_object_arns = [
            self.bucket.arn_for_objects(f"{self.ARTIFACTS_JSON_PREFIX}/*"),
            self.bucket.arn_for_objects(f"{self.ARTIFACTS_EXCEL_PREFIX}/*"),
            self.bucket.arn_for_objects(f"{self.TEMP_DATA_PREFIX}/*"),
        ]

        statements.extend(
            [
                iam.PolicyStatement(
                    sid="AllowLambdaLogging",
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=log_group_arns,
                ),
                iam.PolicyStatement(
                    sid="AllowS3ObjectAccess",
                    actions=["s3:GetObject", "s3:PutObject"],
                    resources=artifact_object_arns,
                ),
                iam.PolicyStatement(
                    sid="AllowS3ListArtifactsPrefix",
                    actions=["s3:ListBucket"],
                    resources=[self.bucket.bucket_arn],
                    conditions={
                        "StringLike": {
                            "s3:prefix": [
                                f"{self.ARTIFACTS_JSON_PREFIX}/",
                                f"{self.ARTIFACTS_JSON_PREFIX}/*",
                                f"{self.ARTIFACTS_EXCEL_PREFIX}/",
                                f"{self.ARTIFACTS_EXCEL_PREFIX}/*",
                                f"{self.TEMP_DATA_PREFIX}/",
                                f"{self.TEMP_DATA_PREFIX}/*",
                            ]
                        }
                    },
                ),
            ]
        )

        iam.Policy(
            self,
            "LambdaExecutionPolicy",
            statements=statements,
        ).attach_to_role(self.execution_role)

        self.artifact_reader_policy = iam.ManagedPolicy(
            self,
            "ArtifactsReadManagedPolicy",
            managed_policy_name=f"ReleaseCopilot-{self.environment_name}-ArtifactsRead",
            statements=[
                iam.PolicyStatement(
                    sid="AllowArtifactReads",
                    actions=[
                        "s3:GetObject",
                        "s3:GetObjectVersion",
                        "s3:GetObjectTagging",
                    ],
                    resources=[
                        self.bucket.arn_for_objects(f"{self.ARTIFACTS_JSON_PREFIX}/*"),
                        self.bucket.arn_for_objects(f"{self.ARTIFACTS_EXCEL_PREFIX}/*"),
                    ],
                ),
                iam.PolicyStatement(
                    sid="AllowArtifactList",
                    actions=["s3:ListBucket"],
                    resources=[self.bucket.bucket_arn],
                    conditions={
                        "StringLike": {
                            "s3:prefix": [
                                f"{self.ARTIFACTS_JSON_PREFIX}/",
                                f"{self.ARTIFACTS_JSON_PREFIX}/*",
                                f"{self.ARTIFACTS_EXCEL_PREFIX}/",
                                f"{self.ARTIFACTS_EXCEL_PREFIX}/*",
                            ]
                        }
                    },
                ),
            ],
        )

        self.artifact_writer_policy = iam.ManagedPolicy(
            self,
            "ArtifactsWriteManagedPolicy",
            managed_policy_name=f"ReleaseCopilot-{self.environment_name}-ArtifactsWrite",
            statements=[
                iam.PolicyStatement(
                    sid="AllowArtifactWrites",
                    actions=[
                        "s3:PutObject",
                        "s3:PutObjectTagging",
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject",
                        "s3:GetObject",
                    ],
                    resources=[
                        self.bucket.arn_for_objects(f"{self.ARTIFACTS_JSON_PREFIX}/*"),
                        self.bucket.arn_for_objects(f"{self.ARTIFACTS_EXCEL_PREFIX}/*"),
                        self.bucket.arn_for_objects(f"{self.TEMP_DATA_PREFIX}/*"),
                    ],
                ),
                iam.PolicyStatement(
                    sid="AllowArtifactWriteList",
                    actions=["s3:ListBucket"],
                    resources=[self.bucket.bucket_arn],
                    conditions={
                        "StringLike": {
                            "s3:prefix": [
                                f"{self.ARTIFACTS_JSON_PREFIX}/",
                                f"{self.ARTIFACTS_JSON_PREFIX}/*",
                                f"{self.ARTIFACTS_EXCEL_PREFIX}/",
                                f"{self.ARTIFACTS_EXCEL_PREFIX}/*",
                                f"{self.TEMP_DATA_PREFIX}/",
                                f"{self.TEMP_DATA_PREFIX}/*",
                            ]
                        }
                    },
                ),
            ],
        )

    def _resolve_secret(
        self,
        construct_id: str,
        *,
        provided_arn: Optional[str],
        description: str,
        secret_name: str,
    ) -> secretsmanager.ISecret:
        if provided_arn:
            return secretsmanager.Secret.from_secret_complete_arn(self, construct_id, provided_arn)
        return secretsmanager.Secret(
            self,
            construct_id,
            description=description,
            secret_name=secret_name,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
            ),
        )

    def _configure_alarm_action(self) -> actions.IAlarmAction | None:
        alarm_email = (self.node.try_get_context("alarmEmail") or "").strip()
        if not alarm_email:
            return None

        topic = sns.Topic(self, "ReleaseCopilotAlarmTopic")
        topic.add_subscription(subs.EmailSubscription(alarm_email))
        return actions.SnsAction(topic)

    def _add_lambda_alarms(self) -> None:
        errors_metric = self.lambda_function.metric_errors(
            period=Duration.minutes(5), statistic="sum"
        )
        throttles_metric = self.lambda_function.metric_throttles(
            period=Duration.minutes(5), statistic="sum"
        )

        errors_alarm = cw.Alarm(
            self,
            "LambdaErrorsAlarm",
            metric=errors_metric,
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        throttles_alarm = cw.Alarm(
            self,
            "LambdaThrottlesAlarm",
            metric=throttles_metric,
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        if self._alarm_action:
            errors_alarm.add_alarm_action(self._alarm_action)
            throttles_alarm.add_alarm_action(self._alarm_action)

    def _add_reconciliation_dlq_alarm(self) -> None:
        dlq_metric = self.reconciliation_dlq.metric_approximate_number_of_messages_visible(
            period=Duration.minutes(5),
            statistic="sum",
        )

        dlq_alarm = cw.Alarm(
            self,
            "JiraReconciliationDlqMessagesVisibleAlarm",
            metric=dlq_metric,
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            alarm_description=(
                "ReleaseCopilot reconciliation DLQ has visible messages requiring triage"
            ),
        )

        if self._alarm_action:
            dlq_alarm.add_alarm_action(self._alarm_action)

    def _add_schedule(self, *, schedule_enabled: bool, schedule_cron: str | None) -> None:
        """Provision the optional EventBridge rule when scheduling is enabled.

        Skipping creation when ``schedule_enabled`` is false ensures the stack
        deletes any previously-deployed schedule during updates.
        """
        if not schedule_enabled:
            return

        expression = schedule_cron or "cron(30 1 * * ? *)"
        rule = events.Rule(
            self,
            "ReleaseCopilotSchedule",
            schedule=events.Schedule.expression(expression),
        )
        rule.add_target(targets.LambdaFunction(self.lambda_function))

    def _add_reconciliation_schedule(
        self,
        *,
        enable_schedule: bool,
        schedule_expression: str | None,
    ) -> None:
        if not enable_schedule:
            return

        expression = schedule_expression or "cron(15 7 * * ? *)"
        rule = events.Rule(
            self,
            "JiraReconciliationSchedule",
            schedule=events.Schedule.expression(expression),
        )
        rule.add_target(
            targets.LambdaFunction(
                self.reconciliation_lambda,
                retry_attempts=2,
                max_event_age=Duration.hours(2),
                dead_letter_queue=self.reconciliation_dlq,
            )
        )
