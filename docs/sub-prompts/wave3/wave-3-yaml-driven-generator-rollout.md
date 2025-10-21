# Wave 3 – Sub-Prompt · [AUTO] Wave 3 – YAML-driven generator rollout

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Generate the MOP, sub-prompts, issue bodies, and manifest from this spec.
- Archive the previous wave MOP exactly once per day when present.
- Provide a Make/CI/pre-commit guard that detects drift.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Enhance generator pipeline in `main.py` or `tools/generator/` to read the YAML spec and emit MOP, sub-prompts, issue bodies, and manifest files under `docs/sub-prompts/wave3/` and `backlog/`.
- Implement archiver `tools/generator/archive.py` to compress previous wave MOP once per day, storing in `artifacts/issues/archive/` with Phoenix timestamp metadata.
- Add drift detection guard invoked via Make/CI/pre-commit (e.g., `scripts/ci/check_generator_drift.sh`) that runs the generator and compares outputs using `git diff --exit-code`.
- Sequence: generator updates → archiver scheduling (idempotent daily check) → guard script integration → docs/tests.

### Key code snippets
```python
# tools/generator/archive.py
def archive_previous_wave(now: datetime | None = None) -> Path | None:
    """Archive prior wave MOP at most once per Phoenix day."""

    zone = ZoneInfo("America/Phoenix")
    today = (now or datetime.now(tz=zone)).strftime("%Y-%m-%d")
    marker = artifacts_dir / f"archive_{today}.lock"
    if marker.exists():
        return None
    marker.write_text("archived", encoding="utf-8")
    return create_tarball(source=previous_wave_dir, dest=artifacts_dir / f"wave2_{today}.tar.gz")
```

```bash
# scripts/ci/check_generator_drift.sh
#!/usr/bin/env bash
set -euo pipefail
python main.py generate --timezone America/Phoenix
git diff --stat --exit-code docs/sub-prompts/wave3 prompts backlog || {
  echo "Generator drift detected" >&2
  exit 1
}
```

```python
# main.py excerpt
if __name__ == "__main__":
    parser.add_argument("generate", ...)
    parser.add_argument("--timezone", default="America/Phoenix")
```

### Tests (pytest; no live network)
- `tests/generator/test_generate_outputs.py::test_generate_from_yaml_creates_manifest` ensures all files are produced and match expected fixtures.
- `tests/generator/test_archive.py::test_archive_runs_once_per_day` checks lockfile behavior and Phoenix timezone usage.
- `tests/generator/test_drift_guard.py::test_drift_guard_detects_changes` invokes guard script via subprocess in temp repo.
- Edge cases: missing previous wave directory, YAML spec missing fields, timezone conversions crossing midnight.
- Maintain ≥70% coverage on generator modules with `pytest tests/generator --cov=tools.generator`.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/generator.md`:

> Run `python main.py generate --timezone America/Phoenix` to refresh Wave 3 artifacts. The generator archives the prior wave MOP once per Phoenix day, writing tarballs to `artifacts/issues/archive/`. CI/pre-commit executes `scripts/ci/check_generator_drift.sh` to ensure repo state matches generated outputs.

Update `README.md` automation section with drift guard details.

### Risk & rollback
- Risks: generator overwriting manual edits, archiver running multiple times if lockfiles missing, drift guard blocking CI on expected changes.
- Rollback: revert generator/archiver scripts and remove guard script from CI; restore previous artifacts from git.
- No data migrations; archive outputs stored separately.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Run generator unit tests with coverage, ruff/black on scripts, and manual `scripts/ci/check_generator_drift.sh` dry run.
- Validate archive tarballs include Phoenix timestamp metadata without embedding secrets.
- Confirm drift guard respects clean git state and excludes ephemeral files.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Roll out YAML-driven generator with archiving and drift guard.
- **Note:** Daily archive lockfiles prevent multiple tarballs per Phoenix day.
- **Action:** Update generator scripts, add drift check, and document workflow.
