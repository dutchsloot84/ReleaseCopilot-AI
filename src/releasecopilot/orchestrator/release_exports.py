"""Release note and validation document orchestration helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping

from config.loader import Defaults
from config.settings import load_settings
from export.release_notes import (
    flatten_grouped_notes,
    group_release_notes,
    serialise_grouped_notes,
)
from releasecopilot.logging_config import get_logger
from releasecopilot.orchestrator.artifacts import (
    PHOENIX_TZ,
    ArtifactWriteError,
    generate_run_metadata,
    write_release_notes_artifacts,
    write_validation_artifact,
)
from releasecopilot.orchestrator.validation_doc import (
    ValidationDocPayload,
    build_validation_doc,
)
from ui.data_source import load_local_reports

LOGGER = get_logger(__name__)


class ReleaseExportError(RuntimeError):
    """Raised when the release export orchestration fails."""


@dataclass(frozen=True)
class ReleaseExportResult:
    release_notes: Mapping[str, Path]
    validation: Mapping[str, Path]

    def as_dict(self) -> dict[str, dict[str, str]]:
        return {
            "release_notes": {name: str(path) for name, path in self.release_notes.items()},
            "validation": {name: str(path) for name, path in self.validation.items()},
        }


def _ensure_issue_sequence(payload: object) -> list[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in ("issues", "items", "stories"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, Mapping)]
    return []


def _load_issue_catalog(reports_dir: Path) -> list[Mapping[str, Any]]:
    direct_path = reports_dir / "issues.json"
    if direct_path.exists():
        try:
            payload = json.loads(direct_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = []
        return _ensure_issue_sequence(payload)

    issues_dir = reports_dir / "issues"
    if issues_dir.exists() and issues_dir.is_dir():
        issues: list[Mapping[str, Any]] = []
        for file_path in sorted(issues_dir.glob("*.json")):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, Mapping):
                issues.append(payload)
        return issues
    return []


def _fallback_issues(report_data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    issues: list[Mapping[str, Any]] = []
    for mapping in report_data.get("commit_story_mapping", []):
        if not isinstance(mapping, Mapping):
            continue
        key = mapping.get("story_key") or mapping.get("issue_key")
        if not isinstance(key, str) or not key:
            continue
        issues.append(
            {
                "key": key,
                "summary": mapping.get("story_summary") or mapping.get("summary") or "",
                "issue_type": mapping.get("story_type") or mapping.get("issue_type"),
            }
        )
    return issues


def _resolve_base_url(settings: Mapping[str, Any]) -> str | None:
    jira_cfg = settings.get("jira") if isinstance(settings, Mapping) else None
    if isinstance(jira_cfg, Mapping):
        base_url = jira_cfg.get("base_url")
        if isinstance(base_url, str) and base_url.strip():
            return base_url.rstrip("/")
    return None


def run_release_exports(
    *,
    reports_dir: Path,
    artifact_root: Path,
    defaults: Defaults,
    run_id: str | None = None,
    git_sha: str | None = None,
    now: datetime | None = None,
) -> ReleaseExportResult:
    """Generate release notes and validation artifacts from the latest report."""

    try:
        report_payload = load_local_reports(reports_dir)
    except Exception as exc:  # pragma: no cover - propagate as orchestrator error
        raise ReleaseExportError(f"Unable to load reports from {reports_dir}: {exc}") from exc

    report_data = report_payload.get("data")
    if not isinstance(report_data, Mapping):
        raise ReleaseExportError("Report JSON is missing the expected mapping payload")

    settings = load_settings(defaults_path=defaults.settings_path)
    base_url = _resolve_base_url(settings)

    explicit_issues = _load_issue_catalog(Path(reports_dir))
    if explicit_issues:
        issues = explicit_issues
    else:
        issues = _fallback_issues(report_data)

    metadata = generate_run_metadata(run_id=run_id, git_sha=git_sha, now=now, tz=PHOENIX_TZ)

    grouped_notes = group_release_notes(issues, base_url=base_url)
    notes_payload = serialise_grouped_notes(grouped_notes)
    note_rows = flatten_grouped_notes(grouped_notes)

    validation_payload: ValidationDocPayload = build_validation_doc(
        issues=issues,
        settings=settings,
        base_url=base_url,
    )

    release_notes_dir = artifact_root / "release_notes"
    validation_dir = artifact_root / "validation"

    try:
        release_outputs = write_release_notes_artifacts(
            grouped_notes=notes_payload,
            tabular_rows=note_rows,
            metadata=metadata,
            out_dir=release_notes_dir,
        )
        validation_outputs = write_validation_artifact(
            items=validation_payload["items"],
            field_id=str(validation_payload["deployment_notes_field_id"]),
            metadata=metadata,
            out_dir=validation_dir,
        )
    except ArtifactWriteError as exc:
        raise ReleaseExportError(str(exc)) from exc

    LOGGER.info(
        "Release exports generated",
        extra={
            "run_id": metadata.run_id,
            "git_sha": metadata.git_sha,
            "release_notes": {name: str(path) for name, path in release_outputs.items()},
            "validation": {name: str(path) for name, path in validation_outputs.items()},
        },
    )

    return ReleaseExportResult(release_notes=release_outputs, validation=validation_outputs)


__all__ = ["ReleaseExportError", "ReleaseExportResult", "run_release_exports"]
