# Release Artifacts Runbook

**Decision:** Automate release-note and validation-doc exports with Phoenix-stamped metadata sourced from the orchestrator pipeline.

**Note:** Deployment Notes field IDs remain configurable via `config/defaults.yml`/`config/settings.yaml`; adjust to match environment-specific Jira custom fields.

**Action:** Generate artifacts with `rc orchestrator release-export`, confirm JSON/Excel payloads include `run_id`, `git_sha`, and `generated_at` in America/Phoenix, then surface downloads in the Streamlit UI.

The Wave 3 automation streamlines stakeholder sign-off by producing grouped release notes and validation documentation directly from the latest audit reports. Outputs land under `artifacts/release_notes/` and `artifacts/validation/`, both stamped with Phoenix-local metadata for traceability.

## Workflow

1. Run the offline audit (`rc audit ...`) to refresh `reports/` with the latest JSON/Excel bundle.
2. Execute `rc orchestrator release-export --reports-dir reports --artifact-root artifacts`.
3. Inspect the Phoenix-aware metadata recorded in each artifact (`run_id`, `git_sha`, `generated_at`, `timezone`).
4. Download the deliverables from the Streamlit dashboard; the Orphan tab now includes Release Notes and Validation Doc controls once artifacts exist.

## Validation Notes

- JSON artifacts adhere to the schemas in `artifacts/release_notes/run.schema.json` and `artifacts/validation/run.schema.json`.
- Excel artifacts ship with a `Metadata` sheet alongside change-type worksheets and a validation worksheet.
- Deployment Notes are sourced from the configurable field ID and rendered as Markdown text for human review.

## Rollback

If export behaviour regresses, delete the generated files under `artifacts/release_notes/` and `artifacts/validation/`, revert the orchestrator/UI changes, and fall back to manual sharing of audit outputs.
