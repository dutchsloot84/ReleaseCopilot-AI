"""Utilities for persisting correlation artifacts with Phoenix metadata."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping, Sequence
import uuid
from zoneinfo import ZoneInfo

from matcher.engine import match
from releasecopilot.gaps.api import (
    GapResponse,
    commits_without_story as build_commits_gap,
    stories_without_commits as build_stories_gap,
)

PHOENIX_TZ = ZoneInfo("America/Phoenix")


def _resolve_git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - defensive
        return "unknown"
    sha = result.stdout.strip()
    return sha or "unknown"


def _ensure_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(key): val for key, val in value.items()}
    raise TypeError("summary payloads must be mappings")


def _ensure_sequence(data: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if data is None:
        return []
    values: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, Mapping):
            values.append({str(key): val for key, val in item.items()})
    return values


def build_correlation_document(
    *,
    issues: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    commits: Sequence[Mapping[str, Any]] | Iterable[Mapping[str, Any]],
    args: Mapping[str, Any] | None = None,
    run_id: str | None = None,
    git_sha: str | None = None,
    generated_at: datetime | str | None = None,
    tz: ZoneInfo | None = None,
) -> dict[str, Any]:
    """Build a correlation document with Phoenix-aware metadata."""

    zone = tz or PHOENIX_TZ
    identifier = run_id or uuid.uuid4().hex
    resolved_git_sha = git_sha or _resolve_git_sha()

    issues_payload = _ensure_sequence(issues)
    commits_payload = _ensure_sequence(commits)

    matched, missing, orphans, summary = match(issues_payload, commits_payload)
    summary_payload = _ensure_mapping(summary)
    summary_payload.setdefault("matched_commits", len(matched))

    stories_gap: GapResponse = build_stories_gap(
        missing,
        run_id=identifier,
        git_sha=resolved_git_sha,
        args=args,
        generated_at=generated_at,
        tz=zone,
    )
    commits_gap: GapResponse = build_commits_gap(
        orphans,
        run_id=identifier,
        git_sha=resolved_git_sha,
        args=args,
        generated_at=generated_at,
        tz=zone,
    )

    timestamp = stories_gap.generated_at

    document = {
        "run_id": identifier,
        "git_sha": resolved_git_sha,
        "generated_at": timestamp,
        "timezone": zone.key if hasattr(zone, "key") else str(zone),
        "args": _ensure_mapping(args),
        "summary": summary_payload,
        "matched": _ensure_sequence(matched),
        "stories_without_commits": stories_gap.to_dict(),
        "commits_without_story": commits_gap.to_dict(),
    }
    return document


def write_correlation_artifact(
    document: Mapping[str, Any],
    *,
    artifact_dir: Path,
) -> Path:
    """Persist the correlation document and update cache files."""

    if not isinstance(document, Mapping):
        raise TypeError("document must be a mapping")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    run_id = str(document.get("run_id") or uuid.uuid4().hex)
    destination = artifact_dir / f"correlation_{run_id}.json"

    with destination.open("w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2)

    latest = artifact_dir / "latest.json"
    with latest.open("w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2)

    summary_path = artifact_dir / "latest_summary.json"
    summary_payload = {
        "run_id": run_id,
        "generated_at": document.get("generated_at"),
        "timezone": document.get("timezone"),
        "args": document.get("args", {}),
        "summary": document.get("summary", {}),
    }
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2)

    return destination


__all__ = ["build_correlation_document", "write_correlation_artifact"]
