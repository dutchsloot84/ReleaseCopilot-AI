## Correlation & Gaps Engine

Generated automatically from backlog/wave3.yaml on 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST).

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Link rules: message > branch > PR title.
- Gaps endpoints: stories-without-commits, commits-without-story.
- Persist run metadata (args, git_sha, generated_at).
- Unit tests for edge cases/collisions.

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

**Labels:** wave:wave3, mvp, area:core, priority:high