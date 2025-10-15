# releasecopilot-ai

Releasecopilot AI automates release audits by correlating Jira stories with Bitbucket commits and exporting structured reports. The project ships with a modular Python codebase, Docker packaging, and AWS primitives for Lambda or container-based execution. This project is distributed under the [MIT License](LICENSE).

> **Weekly Git Historian:** Our scheduled [`weekly-history`](.github/workflows/weekly-history.yml) workflow lints the repository's
> GitHub Actions definitions with `actionlint` and publishes momentum snapshots every Monday at 14:00 UTC. Trigger it manually
> from the **Actions** tab to generate an on-demand report.

## LLM Workflow: MOP + Prompt Chaining (Quickstart)
1. Read the active MOP: `project/prompts/wave1/mop_wave1_security.md`.
2. Generate or update a sub-prompt in `project/prompts/wave1` (use `project/prompts/wave1/subprompt_template.md`).
3. Capture the implementation in a Prompt Recipe (`project/prompts/prompt_recipes/template.md`) and link it in the PR body.
4. Log any manual follow-ups in `actions/pending_actions.json`; CI will surface them with `tools/render_actions_comment.py`.
5. Run the **Critic Check** (`prompts/critic_check.md`) and `python tools/validate_prompts.py` before opening a PR with **Decision / Note / Action** markers.
6. After merge: confirm the action comment is resolved and update historian records.

See `docs/promptops/MOP_Workflow.md` and `docs/promptops/Prompt_Recipe_Guide.md` for end-to-end guidance.

## Features

- Fetch Jira issues for a given fix version using OAuth 3LO tokens.
- Retrieve Bitbucket Cloud commits for configurable repositories and branches.
- Detect stories without commits and commits without linked stories.
- Export release audit results to JSON and Excel files.
- Persist raw API payloads for historical analysis and resume support.
- Upload artifacts to Amazon S3 and leverage Secrets Manager for credentials.
- Ready for container deployment or invocation via AWS Lambda.

## Project Layout

```
releasecopilot-ai/
├── main.py
├── clients/
├── processors/
├── exporters/
├── aws/
├── config/
├── data/
├── temp_data/
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

- **clients/** – API integrations for Jira, Bitbucket, and secret retrieval.
- **processors/** – Business logic to correlate stories and commits.
- **exporters/** – JSON and Excel exporters for the audit report.
- **aws/** – Lambda entry point and S3 helpers.
- **config/** – YAML configuration including AWS and workspace defaults.
- **data/** – Final audit outputs.
- **temp_data/** – Cached raw API responses for resuming and auditing.

## Prerequisites

- Python 3.11+
- Access to Jira Cloud with OAuth 3LO configured.
- Bitbucket Cloud workspace access (OAuth token or username + app password).
- Optional AWS account with permissions for Secrets Manager and S3.

Install Python dependencies locally:

```bash
pip install -r requirements.txt
```

Optional helpers (such as loading a local `.env` file) live in
`requirements-optional.txt`:

```bash
pip install -r requirements-optional.txt
```

## Configuration

1. Copy `.env.example` to `.env` for local development and populate the placeholders with test credentials. The file is `.gitignore`d—keep real secrets out of version control.
2. Install the optional dependency with `pip install -r requirements-optional.txt` to enable automatic loading of the `.env` file.
3. Review `config/defaults.yml` for the canonical configuration shape. Provide environment-specific overrides in `config/settings.yaml` (optional) or via CLI flags.
4. Store production credentials in AWS Secrets Manager using JSON keys that match the environment variable names (e.g., `JIRA_CLIENT_ID`, `BITBUCKET_APP_PASSWORD`).

Configuration precedence is:

1. CLI flags and override files (`config/settings.yaml`) (highest priority)
2. Environment variables, including values sourced from `.env`
3. AWS Secrets Manager payloads referenced in `config/defaults.yml`
4. Canonical defaults (`config/defaults.yml`)

For non-local deployments, rely on AWS Secrets Manager wherever possible and only fall back to `.env` for iterative development.

## CLI Usage

Release Copilot ships with a subcommand-based CLI. The primary workflow is the
offline audit pipeline which consumes cached Jira and Bitbucket payloads and
regenerates the export artifacts without performing any live API calls.

Generate artifacts from cached inputs:

```bash
rc audit \
  --cache-dir temp_data \
  --json dist/audit.json \
  --xlsx dist/audit.xlsx \
  --scope fixVersion=2025.09.20
```

The command above reads the cached JSON payloads stored in `temp_data/`, writes
the regenerated JSON and Excel artifacts to `dist/`, and annotates the execution
scope with the selected fix version.

### Available options

| Flag | Description |
| ---- | ----------- |
| `--cache-dir` | Directory containing cached payloads (default: `temp_data/`). |
| `--json` | Destination path for the JSON artifact (default: `dist/audit.json`). |
| `--xlsx` | Destination path for the Excel artifact (default: `dist/audit.xlsx`). |
| `--summary` | Destination path for the summary JSON (default: `dist/audit-summary.json`). |
| `--scope` | Repeatable key-value metadata entries (for example `--scope fixVersion=2025.09.20`). |
| `--upload` | Optional S3 URI (`s3://bucket/prefix`) that receives the generated artifacts. |
| `--region` | AWS region for uploads (defaults to `AWS_REGION`/`AWS_DEFAULT_REGION`). |
| `--dry-run` | Print the execution plan without touching the filesystem. |
| `--log-level` | Logging verbosity for the current run. |

### Readiness smoke check

Operations teams can verify AWS connectivity without running a full audit by
invoking the readiness probe:

```bash
rc health --readiness --json dist/health.json
```

The command loads the same defaults as the audit workflow and validates
Secrets Manager access, DynamoDB write/delete permissions, S3 object lifecycle,
and webhook secret resolution. The JSON output follows
[`docs/schemas/health.v1.json`](docs/schemas/health.v1.json) and is documented
in [`docs/runbooks/health_smoke.md`](docs/runbooks/health_smoke.md).

For a quick secrets-only smoke test, run `rc health readiness`. The command
prints `OK SECRET_*` or `FAIL SECRET_*` lines after attempting to read the
configured Secrets Manager entries, never logging secret payloads.

### S3 uploads

Supplying `--upload s3://bucket/prefix` stages the generated artifacts and
publishes them to Amazon S3 using server-side encryption. Metadata attached to
each object includes the serialized scope payload (for Historian traceability)
and the `rc-audit` artifact marker, enabling downstream automation to identify
the upload.

ReleaseCopilot’s managed bucket enforces TLS-only traffic, server-side
encryption (SSE-S3), object ownership via `BucketOwnerEnforced`, and a structured
prefix layout:

| Prefix | Purpose | Retention |
| ------ | ------- | --------- |
| `releasecopilot/artifacts/json/` | Versioned JSON exports for audits. | Transition to Standard-IA after 45 days, Glacier Deep Archive after 365 days (retain 5 versions). |
| `releasecopilot/artifacts/excel/` | Versioned Excel exports for audits. | Transition to Standard-IA after 45 days, Glacier Deep Archive after 365 days (retain 5 versions). |
| `releasecopilot/temp_data/` | Intermediate cache for resumable runs. | Expire after 10 days. |
| `releasecopilot/logs/` | Tooling diagnostics pushed alongside artifacts. | Transition to Standard-IA after 30 days, expire after 120 days. |

Reader and writer IAM managed policies scope access to those prefixes so report
consumers can list/read artifacts while the CLI or exporter can upload results
and short-lived cache files without broad bucket permissions.

## Streamlit Dashboard

Explore generated audit reports with the bundled Streamlit UI. The app can open
local JSON outputs or browse reports hosted in Amazon S3.

### Running the app

```bash
streamlit run ui/app.py
```

### Local reports

1. Point the "Reports folder" sidebar field to a directory containing the
   exported `*.json` and (optionally) `*.xlsx` files. The most recent JSON file
   is loaded automatically.
2. A sample fixture is provided at `reports/sample.json` for quick exploration.

### Amazon S3 mode

1. Ensure AWS credentials are available to the process (`AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION` or a configured profile).
2. Enter the bucket name and optional prefix. The dashboard lists runs grouped
   by fix version and execution date. Selecting a run downloads the JSON report
   and offers a presigned link to the Excel workbook when available.

The main view surfaces KPI metrics, filters (fix version, status, assignee,
labels/components, repository, branch, and commit date range), and tables for
stories with commits, stories without commits, and orphan commits. Filtered
tables can be exported as CSV files. A comparison mode allows diffing the
current run against a previous report and integrates with the `#24` diff API via
an optional endpoint field.

## CI pipeline

Every push or pull request that targets `main` or any `feature/*` branch runs the
baseline GitHub Actions workflow defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
The pipeline provisions Python 3.11, installs both the runtime and development
dependencies, runs focused Ruff lint checks (syntax and runtime errors) and the
pytest suite, and invokes the existing packaging helper to build the Lambda
bundle. A follow-up job ensures the infrastructure code synthesises by running
`npx cdk synth -a "python -m infra.cdk.app"` from the repository root with the AWS CDK CLI. When a tag matching
`v*.*.*` is pushed, the packaged `lambda_bundle.zip` artifact is uploaded to the
run for download.

## Infrastructure (CDK)

- [CDK Best Practices (This Repo)](docs/cdk/README.md)
- [CDK CI Runbook](docs/runbooks/cdk-synth-deploy.md)
- [ADR-0001: Adopt root-level `cdk.json` with module entry](docs/adr/ADR-0001-cdk-root-config.md)

## AWS Deployment

### Lambda

1. Build the container image:
   ```bash
   docker build -t releasecopilot-ai .
   ```
2. Push the image to Amazon ECR and create a Lambda function using the image.
3. Provide an execution role with access to:
   - AWS Secrets Manager (for Jira/Bitbucket credentials)
   - Amazon S3 (for storing artifacts)
   - CloudWatch Logs (for observability)
4. Invoke the function with a payload similar to [`aws/event_example.json`](aws/event_example.json).

### ECS/Fargate or Batch

Use the provided `Dockerfile` and pass CLI arguments through task definitions or AWS Batch job parameters. Mount or sync `/data` and `/temp_data` to S3 as part of the workflow if persistent storage is required.

### Deploying to AWS (per environment)

Infrastructure for the audit workflow is defined in `infra/cdk`. Each AWS environment is described by a small JSON/YAML file in `infra/envs/` (examples: [`dev.json`](infra/envs/dev.json), [`prod.json`](infra/envs/prod.json)). The file controls bucket naming, secret names, schedule settings, and other CDK context values.

1. Install the CDK dependencies once:
   ```bash
   pip install -r infra/cdk/requirements.txt
   ```
2. Review or create `infra/envs/<env>.json` with your desired settings. `bucketBase` and `secrets` must be provided.
3. Deploy using the helper script:
   ```bash
   python scripts/deploy_env.py --env dev --package
   ```
   - `--package` ensures `scripts/package_lambda.sh` runs before deployment so the Lambda artifact is up to date.
   - Add `--no-schedule` to disable the optional EventBridge rule regardless of the environment config.
4. The script bootstraps the account if needed (`cdk bootstrap`) and then executes `cdk deploy --require-approval never` with the environment context derived from the configuration file.

### Synth prerequisites

`infra/cdk/app.py` automatically works out the deployment account and region, but `cdk synth` still needs one of the following to succeed:

1. **CDK context:** supply `account`/`region` in `cdk.json`, an `infra/envs/<env>.json` file, or via CLI flags, e.g. `cdk synth -c account=123456789012 -c region=us-west-2`.
2. **AWS credentials:** run `aws configure`, `aws sso login`, or export environment variables so that `boto3` can call `sts:GetCallerIdentity`. The resolved identity is used for the CDK environment automatically.
3. **Explicit environment variables:** export `CDK_DEFAULT_ACCOUNT` (and optionally `CDK_DEFAULT_REGION`) before invoking `cdk synth`.

Any of the above options keeps local developer workflows working while ensuring CI has enough information to synthesise the stacks.

Production buckets are retained by default; set `"retainBucket": false` in non-production configs to allow destruction on stack deletion.

## Secrets Management

- At runtime the application evaluates configuration in the following order: CLI flags → environment variables (including a local `.env` when present) → YAML defaults. When enabled, AWS Secrets Manager still acts as the fallback for secrets that remain unset.
- Secrets should be stored as JSON maps, for example:
  ```json
  {
    "JIRA_CLIENT_ID": "...",
    "JIRA_CLIENT_SECRET": "...",
    "JIRA_ACCESS_TOKEN": "...",
    "JIRA_REFRESH_TOKEN": "...",
    "JIRA_TOKEN_EXPIRY": 1700000000
  }
  ```
- Bitbucket secrets can include either an OAuth access token or a username/app-password pair.
- Secrets Manager entries for the Lambda workloads use canonical names:
  - `SECRET_JIRA` → `releasecopilot/jira/oauth`
  - `SECRET_BITBUCKET` → `releasecopilot/bitbucket/token`
  - `SECRET_WEBHOOK` → `releasecopilot/jira/webhook_secret`
  Document these identifiers in local `.env` files without storing plaintext values.
- `.env` files are intended for local experiments only—use AWS Secrets Manager for shared or deployed environments.

## Outputs

- `data/jira_issues.json` – Jira issues retrieved for the fix version.
- `data/bitbucket_commits.json` – Commits fetched from Bitbucket.
- `data/<prefix>.json` – Structured audit report.
- `data/<prefix>.xlsx` – Multi-tab Excel workbook with summary, gaps, and mapping.

Artifacts are automatically uploaded to Amazon S3 whenever a bucket is configured via `--s3-bucket` (or the corresponding
configuration/env setting). Use `--s3-prefix` to control the destination prefix.

## Docker Compose

To iterate quickly with local services:

```bash
docker-compose run --rm releasecopilot \
  --fix-version 2025.09.20 \
  --repos policycenter claimcenter \
  --develop-only
```

## Logging

Logs are emitted in JSON-friendly format, making them CloudWatch-ready. Adjust log levels through the `LOG_LEVEL` environment variable (defaults to `INFO`).

## Testing & Contribution

- Linting and unit tests can be wired into GitHub Actions as part of CI/CD.
- `temp_data/` retains every raw response; purge periodically if storage becomes large.
- Contributions should include updates to this README when adding new functionality.

## Documentation

Published with MkDocs Material (auto-deployed from `main`):
https://<your-github-username>.github.io/releasecopilot-ai

Edit pages under `docs/` and push to `main` — the site republish is automated by GitHub Actions.

### Deploying with CDK (dev)

```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\Activate
pip install -r infra/cdk/requirements.txt
npx --yes cdk bootstrap
pytest -q
npx --yes cdk synth
npx --yes cdk deploy --require-approval never

# override context if needed
npx --yes cdk deploy \
  --context bucketBase=releasecopilot-artifacts \
  --context jiraSecretArn=arn:aws:secretsmanager:... \
  --context bitbucketSecretArn=arn:aws:secretsmanager:...
```
