# Wave 3 Mission Outline Plan

_Generated at 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST)_

## Purpose
Deliver a repeatable Wave 3 launch process that can be re-run from a single YAML specification while keeping artifacts deterministic for Phoenix (America/Phoenix, no DST).

## Global Constraints
- Phoenix timezone (America/Phoenix, no DST) is authoritative for scheduling, timestamps, and archival suffixes.
- Preserve least-privilege IAM and avoid leaking secrets in generated outputs or logs.
- Make every artifact idempotent: re-running the generator on the same YAML must yield identical files.

## Quality Bar
- Ruff and Black must pass with no diffs.
- mypy succeeds with the repository type hints.
- pytest runs locally with coverage ≥ 70% on touched modules (no live network).

## Sequenced PRs
- **Wave 3 – YAML-driven generator rollout** — 3 acceptance checks
  - Generate the MOP, sub-prompts, issue bodies, and manifest from this spec.
  - Archive the previous wave MOP exactly once per day when present.
  - Provide a Make/CI/pre-commit guard that detects drift.
  _Notes:_
  - Ensure all generated docs call out America/Phoenix (no DST).
  - Reference Decision/Note/Action markers wherever contributors edit outputs.
- **Wave 3 – onboarding and validation** — 3 acceptance checks
  - Document the generator workflow for contributors in README.md.
  - Update CHANGELOG and PR template markers for Decision/Note/Action.
  - Add pytest coverage for archiving, manifests, and idempotency.
  _Notes:_
  - Tests must not hit GitHub APIs; rely on offline fixtures.

## Artifacts & Traceability
- MOP source: `backlog/wave3.yaml`
- Rendered MOP: `docs/mop/mop_wave3.md`
- Sub-prompts: `docs/sub-prompts/wave3/`
- Issue bodies: `artifacts/issues/wave3/`
- Manifest: `artifacts/manifests/wave3_subprompts.json`
- Generated via `make gen-wave3` with Phoenix timestamps.

## Notes & Decisions Policy
- Capture contributor annotations with **Decision:**/**Note:**/**Action:** markers.
- America/Phoenix (no DST) timestamps must accompany status updates.
- Store generated artifacts in Git with deterministic ordering.

## Acceptance Gate
- Validate linting, typing, and tests before marking this wave complete.
- Ensure the manifest SHA (`git_sha`) matches the release commit used for generation.