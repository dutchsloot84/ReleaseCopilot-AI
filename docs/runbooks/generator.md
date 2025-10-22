# Wave Generator Runbook (America/Phoenix)

**Last updated:** 2024-05-22T09:00:00-07:00 (America/Phoenix)

The wave generator converts YAML manifests (e.g., `backlog/wave3.yaml`) into the Mission Outline Plan (MOP), sub-prompts, GitHub
issue bodies, and manifest metadata. Follow this runbook before committing regenerated artifacts.

## Prerequisites

- Python 3.11+ with repository dependencies installed: `pip install -r requirements.txt -r requirements-dev.txt`
- Git workspace synced with the latest `main`
- Phoenix-local awareness. America/Phoenix (UTC-7) is the canonical timezone. Do **not** swap to UTC or daylight-saving offsets.

## Standard Operating Procedure

1. Inspect the source manifest (`backlog/wave3.yaml`) and confirm constraints reference Phoenix explicitly.
2. Resolve deterministic timestamps:
   ```bash
   PYTHONPATH=src:. python -m releasecopilot.cli_releasecopilot generate --spec backlog/wave3.yaml --timezone America/Phoenix
   ```
   - The CLI delegates to `scripts/github/wave2_helper.py generate`, persisting Phoenix timestamps everywhere. After installing the project in editable mode you can substitute the `releasecopilot` console script.
   - A prior wave MOP archive is written to `docs/mop/archive/mop_wave<N-1>_YYYY-MM-DD.md` once per Phoenix day.
3. Validate outputs:
   - `docs/mop/mop_wave3.md`
   - `docs/sub-prompts/wave3/`
   - `artifacts/issues/wave3/`
   - `artifacts/manifests/wave3_subprompts.json`
   - `docs/mop/archive/`
4. Re-run the generator:
   ```bash
   PYTHONPATH=src:. python -m releasecopilot.cli_releasecopilot generate --spec backlog/wave3.yaml --timezone America/Phoenix
   ```
   No diffs should appear; idempotency is enforced by pytest coverage (`tests/generator/`).
5. Execute the generator test suite:
   ```bash
   pytest tests/generator --cov=scripts.github.wave2_helper
   ```
   Ensure Phoenix timestamp assertions and archiver/idempotency coverage pass locally.
6. Update documentation and changelog markers using **Decision / Note / Action** prefixes. Reference
   `artifacts/manifests/wave3_subprompts.json` in PR discussions for traceability.

## Validation Checklist

- [ ] Phoenix timestamps (`America/Phoenix`, `UTC-7`) appear in the MOP, manifest, and archived filenames.
- [ ] `docs/mop/archive/` contains at most one entry per Phoenix day.
- [ ] `pytest tests/generator --cov` succeeds with ≥70% coverage for generator modules.
- [ ] README highlights the generator workflow and links back to this runbook.
- [ ] CHANGELOG and PR template begin status blocks with **Decision:**/**Note:**/**Action:** markers.

## Rollback

If regenerated artifacts drift or timestamps slip out of Phoenix:

1. `git checkout -- docs/mop docs/sub-prompts artifacts/issues artifacts/manifests`
2. Remove `docs/mop/archive/mop_wave*_YYYY-MM-DD.md` created in the broken run.
3. Re-run the generator after confirming local timezone flags (`--timezone America/Phoenix`).
4. Escalate in Slack `#releasecopilot-wave3` with the manifest path and pytest logs attached.

## References

- `backlog/wave3.yaml` – canonical wave spec
- `artifacts/manifests/wave3_subprompts.json` – deterministic manifest with Phoenix timestamps
- `tests/generator/` – pytest suite covering archiving, manifests, and idempotency
