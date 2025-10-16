## Wave 3 – onboarding and validation

Generated automatically from backlog/wave3.yaml on 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST).

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

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.

**Labels:** wave:wave3, documentation, testing