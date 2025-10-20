## [Unreleased]
### Hardened CI Quality Gate
**Decision:** Enforce linting, formatting, typing, and coverage thresholds directly in CI with Phoenix-aligned guidance for contributors.
**Note:** Local and CI runs now share the `ruff check .`, `black --check .`, `mypy --config-file mypy.ini`, and `pytest --cov=src` sequence with America/Phoenix (UTC-7) timeboxing.
**Action:** Added tooling configuration in `pyproject.toml`, centralized network/config stubs in `tests/conftest.py`, hardened `.github/workflows/ci.yml` with explicit lint/type/coverage steps, surfaced coverage summaries via `scripts/ci/coverage_gate.py`, and refreshed README/runbook guidance.
### Wave 3 Onboarding and Validation
**Decision:** Document Wave 3 generator onboarding so contributors can translate `backlog/wave3.yaml` into sub-prompts deterministically.
**Note:** America/Phoenix (UTC-7, no DST) remains the required timezone for manifests, archives, and coverage checks.
**Action:** Added README/runbook guidance, expanded pytest coverage under `tests/generator/`, and aligned PR template markers referencing `artifacts/manifests/wave3_subprompts.json`.

### Wave 3 – Mocked Jira/Bitbucket + Cached Audit Tests
**Decision:** Strengthen Jira/Bitbucket tests using cached payloads and schema contracts (see `artifacts/issues/wave3/tests-mocked-jira-bitbucket-e2e-with-cached-payloads.md`).
**Note:** Cached fixtures must be updated alongside API changes to prevent drift.
**Action:** Added pagination/retry client tests, offline audit E2E coverage, and schema validators guarding JSON/Excel outputs.

### Changed
- **Decision:** Automate import hygiene fixes in CI so ruff/isort guards always run before reviews.
- **Note:** Auto-fix commits are pushed with `[skip ci]` from the GitHub Actions bot and reference America/Phoenix scheduling expectations.
- **Action:** Updated `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, and `pyproject.toml` to apply ruff check --fix + black, auto-commit results, and fail if additional diffs appear.
### Added
- **Decision:** Adopt `python main.py generate --timezone America/Phoenix` as the source of truth for Wave 3 artifacts.
- **Note:** `./scripts/ci/check_generator_drift.sh` reruns the generator and compares `docs/mop/mop_wave3.md`, `docs/sub-prompts/wave3/`, `artifacts/issues/wave3/`, and `artifacts/manifests/wave3_subprompts.json` against the manifest entry.
- **Action:** Introduced `tools/generator/` modules, Phoenix-day archiving, and generator drift guard invoked by Make/CI/pre-commit.
- YAML-driven Wave 3 generator (`scripts/github/wave2_helper.py generate`) emitting the MOP,
  sub-prompts, issue bodies, and manifest with Phoenix timestamps.
- Templated artifacts (`templates/*.j2`) plus backlog spec (`backlog/wave3.yaml`) and
  generated outputs guarded by Make/CI/pre-commit integration.
- Test suite covering archiving, manifest schema, idempotency, and template rendering for
  the new wave generator.
- Wave 2 helper automation CLI for backlog collection, deterministic prioritization,
  prompt seeding, Phoenix-local comment drafts, and PR scaffolding.
- Wave 2 orchestrator CLI with slash-command planning, Phoenix-stamped artifacts,
  and dispatch envelopes for the `orchestrator-runner` workflow.
- GitHub Action automation for `/orchestrate` commands, including Phoenix-timestamped artifacts,
  reusable dispatcher workflow, and comment permission gating.
- Phoenix-ready S3 artifacts bucket hardening: TLS-only bucket policy, bucket-owner enforced ownership, structured prefixes with lifecycle management, and read/write managed policies.
- Artifacts bucket runbook documenting prefix retention, Phoenix-time procedures, and recovery guidance.
- Least-privilege Secrets Manager wiring with secret smoke test CLI and redaction helpers.
- MOP + prompt-chaining scaffolding (`prompts/` templates, runbooks, PR template, Issue form).
- Active MOP index in docs; README quickstart.
- Wave 1 prompt recipe catalog, human-in-the-loop tracking JSON, and CI validation/comment automation.
- Monthly AWS Budgets cost guardrail with SNS/email alerts and manual verification runbook.
- Human actions generator for Wave 2 producing Phoenix-local checklists, calendar stubs,
  activity logging, and updated runbook guidance.
- CI Watchdog workflow with Phoenix-scheduled scans, comment reporting, and
  command-gated autofix safeguards.

### Chore
- Remove placeholderless f-strings flagged by ruff F541.

### Fixed
- Expose CLI functions at the package root to satisfy tests and document the
  supported public interface.
- Align the IAM secrets retrieval policy Sid with infrastructure assertions to
  maintain least-privilege access checks.
- Prefer repository-root `.env` files over package-local ones when
  bootstrapping the CLI environment to honour dotenv precedence expectations.
- Deduplicate Secrets Manager inline policies so exactly four statements remain
  in the synthesized template, matching the Wave 1 least-privilege contract.
- Restore the ``AllowSecretRetrieval`` Sid with explicit secret ARNs while
  keeping the inline policy confined to four least-privilege statements.
- Enforce TLS-only publishing on the BudgetAlerts SNS topic to resolve
  AwsSolutions-SNS3.
