# releasecopilot-ai

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Release-Copilot/ReleaseCopilot-AI/main.svg)](https://results.pre-commit.ci/latest/github/Release-Copilot/ReleaseCopilot-AI/main)

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

Wave 2 human-action orchestration is covered in `docs/promptops/human_actions.md` with
manual procedures in `docs/runbooks/wave2_human_actions.md`. Phoenix operates on
Mountain Standard Time (UTC-7) year-round—no daylight saving adjustments are needed
when scheduling helper or orchestrator checkpoints.

## Features

- Fetch Jira issues for a given fix version using OAuth 3LO tokens.
- Retrieve Bitbucket Cloud commits for configurable repositories and branches.
- Detect stories without commits and commits without linked stories.
- Export release audit results to JSON and Excel files.
- Persist raw API payloads for historical analysis and resume support.
- Upload artifacts to Amazon S3 and leverage Secrets Manager for credentials.
- Ready for container deployment or invocation via AWS Lambda.

### Wave 3 Bitbucket ingest timeline

Wave 3 enables Phoenix-aware Bitbucket ingest across scheduled scans and
webhook deltas. Use `rc ingest bitbucket-scan --hours 4` to backfill commits
within a configurable window and register the `/webhooks/bitbucket` endpoint via
`services/webhooks/bitbucket.py` for push / PR events. Each run stores metadata
in `data/bitbucket/commits.db` and emits artifacts under
`artifacts/issues/wave3/bitbucket/` stamped in America/Phoenix.

### Wave 3 correlation & gaps

**Decision:** Update link precedence and expose Phoenix-stamped gaps endpoints.
**Note:** Artifacts now include input args; document expected payload for consumers.
**Action:** Ship matcher updates, persist metadata, and document new endpoints.

Run `rc matcher correlate --issues data/jira_issues.json --commits data/bitbucket_commits.json`
to produce a Phoenix-aware correlation artifact at `artifacts/issues/wave3/correlation/`. Each
run records `run_id`, `git_sha`, `generated_at`, and CLI args in the America/Phoenix timezone
while surfacing gap payloads for `stories_without_commits` and `commits_without_story`.

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

## Local development workflow

Install development dependencies (formatter, linters, type checker, and pre-commit integration):

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

Set up the shared pre-commit hooks so formatting runs automatically before every commit:

```bash
pre-commit install
```

Run all hooks once to ensure your workspace matches the CI configuration and that Phoenix-stamped logs from the hooks look correct:

```bash
pre-commit run --all-files
```

Quick spot checks without the hook wrapper mirror the CI workflow:

```bash
ruff check . && \
ruff format --check . && \
mypy --config-file pyproject.toml && \
pytest
```

### Linting & pre-commit.ci

- Local: `pre-commit run --all-files` applies ruff fixes, formatting, mypy, and ancillary checks before you push.
- Pull requests: [pre-commit.ci](https://pre-commit.ci/) runs the same hook set, may auto-commit fixes, and reruns its checks once the fixes land.
- GitHub Actions installs the project editable and runs check-only linting via `scripts/ci/run_precommit.sh` (`ruff format --check .`, `ruff check --output-format=github .`, and `mypy --config-file pyproject.toml`); Actions never applies auto-fixes.

### Import hygiene & test isolation

- `tests/conftest.py` seeds a `config.settings` stub with the Phoenix timezone and disables network access by patching `socket.socket` and `socket.create_connection` for the entire session.
- Individual tests must not manipulate `sys.path`, inject modules into `sys.modules`, or import `releasecopilot_bootstrap`; rely on standard imports at the top of the file.
- Import code directly from its package name (for example `from cli.shared import ...`); avoid `src.`-prefixed imports now that the repository enforces a single `src` package root for mypy and ruff.
- Any test that needs custom configuration should patch helpers on the imported module (for example `main.load_settings`) rather than performing ad-hoc bootstrapping.
- Attempts to open outbound sockets raise a `RuntimeError` so network regressions fail fast both locally and in CI.

Hook output timestamps should remain in America/Phoenix (no DST), matching the Mission Outline Plan and ensuring determinism across CI and pre-commit.ci runs.

## Contributing & Quality Gates

- Pull request descriptions must begin with **Decision:**, **Note:**, and **Action:** summaries that align with the generated manifest entry and reference Phoenix (America/Phoenix) scheduling where applicable.
- Confirm ≥70% test coverage on touched code by running `pytest` (configuration lives in `pyproject.toml`), then gate the result locally with `python tools/coverage_gate.py coverage.json --minimum 70 --paths $(git diff --name-only origin/main...HEAD -- '*.py')` before requesting review.
- Acknowledge the lint/type gates explicitly by running `ruff`, `ruff format`, and `mypy` before submitting the PR template checklist.
- Document updates belong alongside code changes; orchestrator-related pull requests should cross-reference [`docs/runbooks/orchestrator.md`](docs/runbooks/orchestrator.md) so reviewers can validate Phoenix-aware plan and dispatch flows.
- Phoenix time (America/Phoenix, UTC-7 year-round) is the canonical timezone for orchestration—include Phoenix-local timestamps in new artifacts and note deviations in the **Note:** section of the PR template.

## Generating Waves (YAML → MOP/Sub-Prompts/Issues)

Wave 3 and later waves are defined in YAML (`backlog/wave3.yaml`). The helper CLI renders the Mission Outline Plan (MOP), sub-prompts, issue bodies, and a JSON manifest directly from that spec.

1. Update `backlog/wave3.yaml` with the new wave metadata, constraints, and sequenced PRs.
2. Run `make gen-wave3` to execute `python main.py generate --spec backlog/wave3.yaml --timezone America/Phoenix`.
3. Inspect regenerated files under:
   - `docs/mop/mop_wave3.md`
   - `docs/sub-prompts/wave3/`
   - `artifacts/issues/wave3/`
   - `artifacts/manifests/wave3_subprompts.json`
   - `docs/mop/archive/` (previous wave MOP archived once per Phoenix day)
4. Validate Phoenix timestamps (America/Phoenix, UTC-7 year-round) in every artifact before committing. The generator runbook (`docs/runbooks/generator.md`) outlines the contributor checklist.
5. Run the generator twice to confirm idempotency, then commit or rerun until `git status` is clean. Wave outputs must remain drift-free across Phoenix days.

### Troubleshooting

**Decision:** Provide CSV fallback flow when Jira JQL retries fail. See [`artifacts/issues/wave3/csv-fallback-for-failed-jira-jql.md`](artifacts/issues/wave3/csv-fallback-for-failed-jira-jql.md) for the Wave 3 manifest entry.
**Note:** CSV exports must include the default Jira columns (Issue key, Summary, Status) for ingestion.
**Action:** When the audit CLI reports a JQL failure after retries, provide the path to a UTF-8 Jira CSV export when prompted. The fallback is timestamped in America/Phoenix for traceability.

- **Jira JQL failures** – After retries are exhausted, the CLI prompts for a CSV export. Supply the path to a Jira export generated with the default column set; invalid paths or malformed CSVs are rejected with a clear Phoenix-stamped status message before re-prompting.
- **CI failure “Generator drift detected”** – Run `make gen-wave3` locally (or execute `./scripts/ci/check_generator_drift.sh`) and commit the resulting diffs. The guard script reruns the generator and blocks PRs when artifacts drift.
- **Archive skipped** – The generator only archives the previous wave MOP once per Phoenix day. Confirm `docs/mop/mop_wave2.md` exists before running the command.
- **Need issue metadata** – Use the existing Wave 2 helper subcommands (for example `python scripts/github/wave2_helper.py collect`) to download issues, then stitch them into the generated sub-prompts manually.

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

### Release exports

Run `rc orchestrator release-export` after an audit completes to generate grouped
release notes and a validation document. The command loads the latest JSON from
`--reports-dir` (default: `reports/`), stamps the outputs with Phoenix-local
metadata (`run_id`, `git_sha`, `generated_at`, `timezone`), and writes artifacts
to `--artifact-root` (default: `artifacts/`). Streamlit surfaces download buttons
for these files once they exist, enabling stakeholders to retrieve Release Notes
and Validation Docs directly from the Orphan tab.

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
- Use cached fixtures by setting `RC_CACHED_PAYLOAD_DIR` before invoking `rc audit`.
  The Wave 3 test prompt (`artifacts/issues/wave3/tests-mocked-jira-bitbucket-e2e-with-cached-payloads.md`)
  documents Phoenix-aware expectations for offline runs.

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
