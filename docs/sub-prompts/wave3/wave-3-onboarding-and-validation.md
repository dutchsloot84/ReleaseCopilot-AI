# Wave 3 – Sub-Prompt · [AUTO] Wave 3 – onboarding and validation

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Document the generator workflow for contributors in README.md.
- Update CHANGELOG and PR template markers for Decision/Note/Action.
- Add pytest coverage for archiving, manifests, and idempotency.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Document generator workflow in `README.md` and `docs/runbooks/generator.md`, outlining how YAML manifests translate to sub-prompts; include Phoenix timezone reminders.
- Update `CHANGELOG.md` with new entries using **Decision/Note/Action** markers referencing Wave 3 onboarding.
- Align `.github/pull_request_template.md` with Decision/Note/Action requirement (coordinated with other tasks).
- Add pytest coverage for generator archiving/idempotency in `tests/generator/test_archiver.py` and `tests/generator/test_manifest.py` using cached fixtures.
- Sequence: write tests first to capture behavior → update docs (README/runbook) → adjust changelog and PR template markers.

### Key code snippets
```python
# tests/generator/test_archiver.py
def test_archive_is_idempotent(tmp_path):
    """Archiver writes identical output on repeated runs."""

    run_once = archive_wave(tmp_path, manifest_path)
    run_twice = archive_wave(tmp_path, manifest_path)
    assert filecmp.cmp(run_once, run_twice, shallow=False)
```

```markdown
# README.md excerpt
## Wave 3 Generator Workflow

1. Update `prompts/wave3.yml` with new missions.
2. Run `python main.py generate --timezone America/Phoenix` to produce sub-prompts.
3. Validate artifacts in `docs/sub-prompts/wave3/` before committing.
```

```markdown
# CHANGELOG.md excerpt
### Wave 3 Onboarding
**Decision:** Publish generator workflow and validation coverage.
**Note:** Phoenix (America/Phoenix) remains the canonical timezone for manifests.
**Action:** Add archiver/manifests pytest coverage and refresh PR template markers.
```

### Tests (pytest; no live network)
- `tests/generator/test_manifest.py::test_manifest_loads_without_side_effects` ensures deterministic parsing.
- `tests/generator/test_archiver.py::test_archive_is_idempotent` verifies repeated runs produce identical outputs.
- `tests/generator/test_archiver.py::test_archive_includes_metadata` checks Phoenix timestamps in archived artifacts.
- Run `pytest tests/generator --cov=prompts --cov=tools.generator` to maintain ≥70% coverage.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/generator.md`:

> Contributors should run `python main.py generate --timezone America/Phoenix` to ensure deterministic timestamps. Archive outputs land in `artifacts/issues/wave3/` with `run_id`, `git_sha`, and `generated_at` metadata.

Update `README.md` onboarding section with step-by-step generator usage and links to Wave 3 validation coverage.

### Risk & rollback
- Risks: misdocumented workflow causing incorrect prompt generation; changelog conflicts; tests flaking due to timestamp handling.
- Rollback: revert README/runbook/changelog updates and remove new tests if they block releases.
- No data migrations; generator artifacts remain file-based.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Run ruff/black/mypy (where applicable) and pytest generator suite with coverage.
- Confirm changelog entries use Decision/Note/Action format.
- Validate archived outputs maintain Phoenix timestamps without random IDs.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Document and validate Wave 3 generator onboarding flow.
- **Note:** Generator commands must use America/Phoenix to remain deterministic.
- **Action:** Update README/runbook/CHANGELOG, align PR template, and add generator tests.