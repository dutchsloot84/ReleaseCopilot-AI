# Wave 3 – Sub-Prompt · [AUTO] Correlation & Gaps Engine

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

### Diff-oriented implementation plan
- Extend `src/matcher/engine.py` to prioritize link resolution in the order: commit message → branch name → PR title, using helper functions located in `src/matcher/link_rules.py`.
- Add `src/releasecopilot/gaps/api.py` exposing endpoints for `stories_without_commits` and `commits_without_story`, returning Phoenix-aware metadata (run args, git_sha, generated_at) serialized via `ZoneInfo("America/Phoenix")`.
- Persist run metadata alongside correlation outputs in `artifacts/issues/wave3/correlation/` via updates to `src/tracking/artifacts.py` or new module `src/tracking/correlation.py`.
- Ensure CLI `rc matcher correlate` (if present) or orchestrator step writes the artifacts and updates existing summary caches.
- Sequence: implement link rules → update engine → create gaps API → persist metadata → update CLI → tests/docs.

### Key code snippets
```python
# src/matcher/link_rules.py
from __future__ import annotations

from typing import Iterable


def extract_story_keys(*, message: str, branch: str | None, pr_title: str | None) -> list[str]:
    """Return unique story keys preferring message > branch > PR title."""

    seen: set[str] = set()
    for source in (message, branch, pr_title):
        if not source:
            continue
        for key in parse_keys(source):
            if key not in seen:
                seen.add(key)
    return sorted(seen)
```

```python
# src/releasecopilot/gaps/api.py
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass(slots=True)
class GapResponse:
    """Serializable response for gaps endpoints with Phoenix metadata."""

    run_id: str
    git_sha: str
    generated_at: str
    timezone: str
    payload: list[dict[str, str]]


def stories_without_commits(data: list[dict[str, str]], *, tz: ZoneInfo | None = None) -> GapResponse:
    zone = tz or ZoneInfo("America/Phoenix")
    now = datetime.now(tz=zone).isoformat(timespec="seconds")
    return GapResponse(run_id=data[0]["run_id"], git_sha=data[0]["git_sha"], generated_at=now, timezone=zone.key, payload=data)
```

```json
// artifacts/issues/wave3/correlation/run.schema.json (excerpt)
{
  "type": "object",
  "required": ["args", "git_sha", "generated_at", "timezone", "stories_without_commits", "commits_without_story"],
  "properties": {
    "timezone": {"const": "America/Phoenix"},
    "args": {"type": "object", "properties": {"window_hours": {"type": "integer"}}}
  }
}
```

### Tests (pytest; no live network)
- `tests/matcher/test_link_rules.py::test_extract_story_keys_order` ensures message precedence over branch and PR title.
- `tests/matcher/test_engine.py::test_match_returns_expected_structures` adds collision scenarios and verifies deterministic outputs.
- `tests/gaps/test_api.py::test_stories_without_commits_includes_metadata` asserts Phoenix timestamps and metadata.
- Edge cases: overlapping keys across sources, empty payloads, collisions with differing case, missing run metadata.
- Maintain cached fixtures under `tests/fixtures/correlation/` for deterministic inputs and ensure ≥70% coverage for new code.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/correlation.md`:

> The Wave 3 correlation engine now resolves story keys by prioritizing commit messages before branch names and PR titles. Gap endpoints (`/api/gaps/stories-without-commits`, `/api/gaps/commits-without-story`) include run metadata stamped in America/Phoenix for downstream auditors.

Update `README.md` API table:

> **Correlation & Gaps** – Provides Phoenix-aware artifacts at `artifacts/issues/wave3/correlation/` with `args`, `git_sha`, and `generated_at` metadata for each run.

### Risk & rollback
- Risks: incorrect precedence causing missing links, schema drift in API responses, timezone misconfigurations.
- Rollback: revert `src/matcher/` and `src/releasecopilot/gaps/` changes; remove artifact schema updates if unused.
- No data migrations required; prior correlation logic can be restored from git history.

## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Run ruff/black/mypy on matcher/gaps modules and execute pytest coverage.
- Validate schema fixtures align with docs; update jsonschema tests accordingly.
- Confirm artifacts embed run metadata and Phoenix timezone before release.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Update link precedence and expose Phoenix-stamped gaps endpoints.
- **Note:** Artifacts now include input args; document expected payload for consumers.
- **Action:** Ship matcher updates, persist metadata, and document new endpoints.
