# AWS baseline and CDK migration

## Manual setup recap

The initial Release Copilot proof-of-concept relied on a manually provisioned IAM execution role with temporary `AdministratorAccess`/`FullAccess` policies, an S3 bucket configured for artifact storage, and Secrets Manager entries for Jira and Bitbucket OAuth credentials. Those steps enabled the prototype but left broad permissions in place and required console-driven configuration management.

## CDK-managed equivalent

The new CDK `CoreStack` codifies those resources with least-privilege defaults:

- **S3 artifacts bucket** &mdash; server-side encrypted with AWS-managed keys, bucket-owner enforced, and non-public. Lifecycle management aligns with the structured prefixes: JSON and Excel artifacts transition to Standard-IA after 45 days and Glacier Deep Archive after 365 days (retaining five non-current versions); `temp_data/` expires after 10 days; and `logs/` shifts to Standard-IA after 30 days then expires at 120 days. Bucket policies deny insecure transport and unencrypted uploads.
- **Secrets** &mdash; existing Jira and Bitbucket secrets can be imported by ARN; when omitted the stack creates placeholders using `SecretStringGenerator` so synthesis/deployment succeed without pre-provisioned secrets.
- **Lambda execution role** &mdash; grants only the actions required to write logs, list the bucket within the `releasecopilot/` hierarchy, read/write the artifacts and `temp_data/` prefixes, and fetch the two exact secrets. The Lambda receives environment variables (`RC_S3_BUCKET`, `RC_S3_PREFIX`, `RC_USE_AWS_SECRETS_MANAGER`) that mirror the manual configuration but are now centrally defined. Dedicated managed policies provide read-only and writer scopes for humans and automation without broadening access.
- **Outputs** &mdash; expose the bucket name and Lambda identifiers for downstream wiring. An optional EventBridge schedule driven by the `scheduleEnabled`/`scheduleCron` context flags can trigger the audit Lambda on a cadence without altering these foundations.

## Migration guidance

1. Deploy the CDK stack in a sandbox account and validate artifact uploads, secret retrieval, and Lambda execution logs.
2. Once validated, deploy to the production account. The stack will create or import the necessary secrets, enforce lifecycle policies, and provision the least-privilege execution role.
3. After the production deployment is confirmed, detach the temporary `FullAccess` policies from the original console-managed role or switch workloads to the CDK-managed role entirely.

## Quick runbook

```bash
# one-time setup
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\Activate
pip install -r infra/cdk/requirements.txt
npx --yes cdk bootstrap

# synth & test
pytest -q
npx --yes cdk synth

# deploy with defaults
npx --yes cdk deploy --require-approval never

# override context for real bucket + secrets
npx --yes cdk deploy \
  --context region=us-west-2 \
  --context bucketName=releasecopilot-artifacts-slv \
  --context jiraSecretArn=arn:aws:secretsmanager:us-west-2:ACCOUNT:secret:/releasecopilot/jira-XXXX \
  --context bitbucketSecretArn=arn:aws:secretsmanager:us-west-2:ACCOUNT:secret:/releasecopilot/bitbucket-YYYY
```

### Quick runbook: CloudWatch alarms

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\Activate
npx --yes cdk synth

# deploy without email
npx --yes cdk deploy --require-approval never

# deploy with email notifications
npx --yes cdk deploy --context alarmEmail=you@example.com --require-approval never

# smoke test: cause a Lambda error, re-invoke, then check CloudWatch Alarms
```

### Optional EventBridge schedule

The stack can create an EventBridge rule that invokes the ReleaseCopilot Lambda on a cron schedule. The feature is disabled by default so the stack stays simple unless you explicitly opt in.

```bash
source .venv/bin/activate  # Windows: .venv\Scripts\Activate

# enable the default 6:30 PM Phoenix schedule (cron(30 1 * * ? *))
npx --yes cdk deploy --context scheduleEnabled=true --require-approval never

# customize the cadence
npx --yes cdk deploy \
  --context scheduleEnabled=true \
  --context scheduleCron="cron(0 14 * * ? *)" \
  --require-approval never

# disable and clean up the rule on the next deploy
npx --yes cdk deploy --context scheduleEnabled=false --require-approval never
```
