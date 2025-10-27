# Wave 3 Mission Outline Plan

_Generated at 2024-01-01T12:00:00-07:00 (America/Phoenix · no DST)_

## Purpose
Ensure sample wave for testing

## Global Constraints
- Respect America/Phoenix scheduling

## Quality Bar
- Maintain ≥70% coverage on generators

## Sequenced PRs
- **Sample PR** — 2 acceptance checks
  - Render mop
  - Render prompts
  _Notes:_
  - Include Phoenix reminder

## Artifacts & Traceability
- MOP source: `backlog/wave3.yaml`
- Rendered MOP: `docs/mop/mop_wave3.md`
- Sub-prompts: `docs/sub-prompts/wave3/`
- Issue bodies: `artifacts/issues/wave3/`
- Manifest: `artifacts/manifests/wave3_subprompts.json`
- Generated via `make gen-wave{wave}` with Phoenix timestamps.

## Notes & Decisions Policy
- Capture contributor annotations with **Decision:**/**Note:**/**Action:** markers.
- America/Phoenix (no DST) timestamps must accompany status updates.
- Store generated artifacts in Git with deterministic ordering.

## Acceptance Gate
- Validate linting, typing, and tests before marking this wave complete.
- Ensure the manifest SHA (`git_sha`) matches the release commit used for generation.
