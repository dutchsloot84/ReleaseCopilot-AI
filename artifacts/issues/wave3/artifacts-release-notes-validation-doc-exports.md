## Artifacts: Release Notes + Validation Doc + Exports

Generated automatically from backlog/wave3.yaml on 2025-10-15T23:23:09-07:00 (America/Phoenix · no DST).

## Context
This task originates from the Wave 3 Mission Outline Plan generated from YAML. Honor America/Phoenix (no DST) for all scheduling data and reference the Decision/Note/Action markers when updating artifacts.

## Acceptance Criteria (from issue)
- Release Notes grouped by type; links to issues.
- Validation Doc uses Deployment Notes field (configurable ID).
- JSON/Excel include run_id, git_sha, generated_at.
- UI download buttons wired.

## Return these 5 outputs
1. Implementation plan covering sequencing and Phoenix-aware timestamps.
2. Code snippets or diffs that satisfy the acceptance criteria.
3. Tests (unit/pytest) demonstrating coverage.
4. Documentation updates referencing this wave's artifacts.
5. Risk assessment noting fallbacks and rollback steps.

### Diff-oriented implementation plan
- Extend `src/export/exporter.py` helpers or add `src/export/release_notes.py` to build grouped release notes (by change type) with issue hyperlinks sourced from existing manifest payloads.
- Introduce `src/releasecopilot/orchestrator/validation_doc.py` that reads the configurable Deployment Notes field ID from config and renders the validation document payload.
- Create Phoenix-stamped artifact writers under `src/tracking/artifacts.py` (e.g., `write_release_notes_artifact`) to emit JSON and Excel with `run_id`, `git_sha`, `generated_at` keyed in `America/Phoenix`.
- Wire UI download buttons in `ui/components/releases.py` (or current release artifacts component) to call new orchestrator endpoints.
- Update orchestrator CLI/handlers (e.g., `src/releasecopilot/orchestrator/run_release_exports.py`) to pipe outputs into `artifacts/release_notes/` and `artifacts/validation/` directories.
- Sequence: schema review → payload builders → artifact writers → orchestrator integration → UI buttons → documentation/tests.

### Key code snippets
```python
# src/export/release_notes.py
from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(slots=True)
class ReleaseNote:
    """Immutable release note entry grouped by type.

    Each entry carries deterministic `issue_key`, `type`, and `summary` fields.
    Secrets must never be logged; timestamps default to America/Phoenix.
    """

    issue_key: str
    type: str
    summary: str
    url: str


def build_grouped_notes(items: list[dict[str, str]]) -> dict[str, list[ReleaseNote]]:
    groups: dict[str, list[ReleaseNote]] = {}
    for item in items:
        note = ReleaseNote(
            issue_key=item["issue_key"],
            type=item.get("type", "unspecified"),
            summary=item.get("summary", ""),
            url=item["url"],
        )
        groups.setdefault(note.type, []).append(note)
    return groups
```

```python
# src/tracking/artifacts.py excerpt
def write_release_artifacts(*, payload: Mapping[str, Any], out_dir: Path, tz: ZoneInfo | None = None) -> Path:
    """Persist release-note exports with Phoenix-aware metadata.

    `payload` must already contain run metadata. The writer appends
    `generated_at` in America/Phoenix and ensures deterministic filenames.
    """

    zone = tz or ZoneInfo("America/Phoenix")
    stamped = {
        **payload,
        "generated_at": datetime.now(tz=zone).isoformat(timespec="seconds"),
        "timezone": zone.key,
    }
    return write_json(out_dir / "release_notes.json", stamped)
```

```json
// artifacts/release_notes/run.schema.json (excerpt)
{
  "type": "object",
  "required": ["run_id", "git_sha", "generated_at", "timezone", "notes"],
  "properties": {
    "timezone": {"const": "America/Phoenix"},
    "notes": {"type": "array", "items": {"$ref": "#/definitions/note"}}
  }
}
```

### Tests (pytest; no live network)
- `tests/export/test_release_notes.py::test_build_grouped_notes_orders_entries` confirms deterministic grouping and hyperlink formatting.
- `tests/orchestrator/test_validation_doc_payload.py::test_uses_deployment_notes_field` mocks config to validate the Deployment Notes field ID lookup.
- `tests/ui/test_release_download_buttons.py::test_buttons_trigger_artifact_download` leverages Streamlit component harness to assert endpoints.
- Edge cases: missing issue URLs, empty change lists, multiple export formats, Excel writer exceptions retried.
- Use fixtures to mock time via `freeze_time("2024-05-01T12:00:00", tz_offset="-07:00")` or `ZoneInfo("America/Phoenix")` ensuring deterministic timestamps; maintain ≥70% coverage across touched modules.

### Docs excerpt (README/runbook)
Add to `docs/runbooks/release-artifacts.md`:

> Wave 3 introduces automated Release Notes grouped by change type with direct issue hyperlinks. After running `rc orchestrator release-export`, download Phoenix-stamped (`America/Phoenix`) JSON/Excel bundles from `artifacts/releases/`. Each bundle includes `run_id`, `git_sha`, and `generated_at` metadata for traceability.

Update `README.md` exports section:

> Validation docs derive the Deployment Notes field (configurable via `config/deployments.yml`) and are saved alongside release exports. UI download buttons surface the latest `artifacts/release_notes/` outputs once optional artifacts are generated.

### Risk & rollback
- Risks: schema drift between JSON/Excel outputs and consumers; incorrect Deployment Notes field IDs; Phoenix timezone misapplied causing compliance gaps.
- Rollback: revert changes in `src/export/`, `src/releasecopilot/orchestrator/`, UI button wiring, and artifact schema files; remove generated docs in `docs/runbooks/` if needed.
- No data migrations occur; deleting the artifacts reverts to previous manual export flow.


## Critic Check
- Re-read the acceptance criteria.
- Confirm Phoenix timezone is referenced wherever scheduling appears.
- Ensure no secrets or credentials are exposed.
- Validate release-note schema matches issue tracker expectations and that Excel/JSON parity tests pass.
- Run ruff/black/mypy plus pytest with coverage enforcement (≥70%) before merging.
- Inspect logs for run metadata only (run_id/git_sha/generated_at) to prevent leaking sensitive payloads.

## PR Markers
- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.
- Link back to the generated manifest entry for traceability.
- **Decision:** Automate release-note and validation-doc exports with Phoenix-stamped metadata.
- **Note:** Deployment Notes field IDs remain configurable; document updates explain how to adjust per environment.
- **Action:** Wire UI download buttons, ensure JSON/Excel include run metadata, and update artifacts documentation.

**Labels:** wave:wave3, mvp, area:artifacts, priority:high