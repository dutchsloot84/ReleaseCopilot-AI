# CI Coverage Gate

**Decision:** Enforce ≥70% pytest-cov threshold and publish Phoenix-stamped PR summaries.
**Note:** Contributors must run the gate locally to prevent CI failures.
**Action:** Add coverage gate script, update CI runner, and integrate PR coverage comment command.

Traceability: `backlog/wave3.yaml` → entry `ci-coverage-gate-pr-summary-comment`.

1. Run `pytest` from the repository root. `pytest.ini` now enables coverage for `src/` and `clients/` with deterministic JSON (`coverage.json`) and XML (`coverage.xml`) reports.
2. Execute `python tools/coverage_gate.py coverage.json --minimum 70 --paths $(git diff --name-only origin/main...HEAD -- '*.py')` to mirror the CI gate. The helper raises `SystemExit` if touched code falls below 70% or if any touched Python file lacks coverage data.
3. When CI runs on a pull request, `python -m releasecopilot.cli pr-comment coverage --file coverage.json --minimum 70 --paths $COVERAGE_PATHS` posts the Phoenix-stamped summary back to the PR thread using the `GITHUB_TOKEN` provided by Actions. The workflow populates `COVERAGE_PATHS` from the diffed Python files.
4. If a failure occurs, re-run the commands locally, add missing tests, and verify that the coverage percentage reported by the gate exceeds the threshold before pushing fixes.

Timestamps in the PR summary use `America/Phoenix` via `ZoneInfo`, ensuring scheduling alignment without DST adjustments.
