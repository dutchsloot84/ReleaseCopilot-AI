# Wave 3 – Sub-Prompt · [AUTO] [Tests] Mocked Jira/Bitbucket + E2E with cached payloads

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Clients covered for pagination, errors, retries (no network).
- E2E audit using cached fixtures verifies schema + content.
- Contract tests guard JSON/Excel schema (jsonschema + column checks).

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Expand `tests/clients/test_jira_client.py` and `tests/clients/test_bitbucket_client.py` to cover pagination, error handling, and retry paths using cached fixtures in `tests/fixtures/jira/` and `tests/fixtures/bitbucket/`.
- Build E2E audit test `tests/e2e/test_audit_cached_payloads.py` orchestrating CLI commands with cached data (no network) and verifying outputs.
- Add JSON Schema validation helper in `tests/helpers/schema_validation.py` referencing artifact schemas for JSON/Excel exports.
- Ensure Phoenix timestamp assertions in E2E artifacts match expected timezone and metadata fields.
- Sequence: update fixtures → expand client tests → implement schema helpers → write E2E test → update docs.

### Key code snippets
```python
# tests/helpers/schema_validation.py
def assert_json_schema(path: Path, schema_path: Path) -> None:
    """Validate JSON file against schema using jsonschema Draft7."""

    data = json.loads(path.read_text())
    schema = json.loads(schema_path.read_text())
    jsonschema.validate(instance=data, schema=schema)
```

```python
# tests/e2e/test_audit_cached_payloads.py
def test_audit_cli_uses_cached_payloads(tmp_path, monkeypatch):
    """Run audit CLI end-to-end with cached Jira/Bitbucket fixtures."""

    monkeypatch.setenv("RC_CACHED_PAYLOAD_DIR", str(Path("tests/fixtures/cached")))
    result = CliRunner().invoke(cli.audit, ["--use-cached-payloads"])
    assert result.exit_code == 0
    artifact = tmp_path / "artifacts" / "audit_results.json"
    assert artifact.exists()
    assert "America/Phoenix" in artifact.read_text()
```

```python
# tests/clients/test_bitbucket_client.py excerpt
def test_iter_commits_handles_pagination(bitbucket_client, mocker):
    pages = [{"values": [...]}, {"values": [...], "next": None}]
    mocker.patch.object(bitbucket_client, "_request", side_effect=pages)
    commits = list(bitbucket_client.iter_commits(repo="org/repo", since=window_start))
    assert len(commits) == sum(len(page["values"]) for page in pages)
```

### Tests (pytest; no live network)
- Run `pytest tests/clients/test_jira_client.py::test_paginated_results` and similar coverage for retries/errors.
- Execute `pytest tests/e2e/test_audit_cached_payloads.py::test_audit_cli_uses_cached_payloads` verifying artifact schema and Phoenix metadata.
- Schema contract tests: `tests/contracts/test_artifact_schemas.py::test_json_export_schema` and `test_excel_columns` ensure column names and order.
- Edge cases: missing pagination `next`, HTTP errors with retries, corrupted cached fixture, Excel column mismatch.
- Ensure coverage >70% for affected modules via `pytest --cov=clients --cov=src/releasecopilot`.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/testing.md`:

> Cached Jira/Bitbucket fixtures live under `tests/fixtures/cached/`. Run `pytest tests/e2e/test_audit_cached_payloads.py --cov` to validate audit flows without network calls. Artifact schema checks rely on JSON Schema files stored alongside artifacts.

Update `README.md` testing section:

> Use `RC_CACHED_PAYLOAD_DIR` to point CLI commands at deterministic fixtures. Phoenix timestamps are validated during E2E runs to maintain timezone consistency.

### Risk & rollback
- Risks: fixture drift causing brittle tests, schema updates breaking contract tests, longer CI durations.
- Rollback: revert new tests/helpers, remove cached fixture references, and restore prior pytest config.
- No data migrations; fixtures remain local files.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Verify fixtures scrub sensitive data before committing.
- Run ruff/black on new test helpers and ensure pytest coverage threshold met.
- Validate Excel tests use cached files without network.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Strengthen Jira/Bitbucket tests using cached payloads and schema contracts.
- **Note:** Cached fixtures must be updated alongside API changes to prevent drift.
- **Action:** Add pagination/retry tests, E2E audit, and contract validators.