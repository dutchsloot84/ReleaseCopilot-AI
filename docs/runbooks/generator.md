# Wave Generator Runbook (America/Phoenix)

**Decision:** Operate the YAML-driven generator via `python main.py generate` so all Wave 3 artifacts remain deterministic.
**Note:** The generator archives the previous wave's MOP once per Phoenix day, storing tarballs under `artifacts/issues/archive/` with a Phoenix timestamp and lockfile.
**Action:** Run the drift guard (`./scripts/ci/check_generator_drift.sh`) locally or in CI to ensure committed artifacts match regenerated output.

## Overview

The generator consumes `backlog/wave3.yaml` and emits:

- Mission Outline Plan (MOP): `docs/mop/mop_wave3.md`
- Sub-prompts: `docs/sub-prompts/wave3/`
- Issue bodies: `artifacts/issues/wave3/`
- Manifest: `artifacts/manifests/wave3_subprompts.json`

All timestamps and scheduling guidance use **America/Phoenix** (no DST).

## Daily workflow

1. Pull latest main branch and ensure dependencies are installed (`pip install -r requirements-dev.txt`).
2. Generate artifacts:
   ```bash
   python main.py generate --spec backlog/wave3.yaml --timezone America/Phoenix
   ```
   - Re-runs are idempotent. When rerun on the same Phoenix day the generator will skip archiving if a lockfile exists.
3. Verify the archive: if `docs/mop/mop_wave2.md` exists the command creates `artifacts/issues/archive/wave2_<YYYY-MM-DD>.tar.gz` plus a `.lock` file tagged with the Phoenix date.
4. Run the drift guard:
   ```bash
   ./scripts/ci/check_generator_drift.sh
   ```
   - CI and pre-commit invoke this guard automatically.
5. Review updated files, confirm Phoenix timestamps, and commit the changes with Decision/Note/Action markers as needed.

## Troubleshooting

- **Missing templates** – Ensure `templates/mop.md.j2`, `subprompt.md.j2`, and `issue_body.md.j2` exist. Copy them from `templates/` if using a temporary workspace.
- **Archive not created** – The previous wave MOP must exist. Confirm `docs/mop/mop_wave2.md` or pass `--no-archive` if intentionally skipping archiving for dry runs.
- **Timezone drift** – Always pass `--timezone America/Phoenix` (default) to maintain Phoenix timestamps.
- **Drift guard failure** – Inspect `git diff` after the guard runs; it indicates which generated files diverge. Regenerate and recommit.

## Traceability

After generation, the manifest includes the Git SHA (`git_sha`), Phoenix timestamp, and all generated slugs. Reference the manifest entry when citing sub-prompts in changelog updates or PR descriptions.
