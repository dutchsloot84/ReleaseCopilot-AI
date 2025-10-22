"""Builders for Phoenix-stamped validation document payloads."""

from __future__ import annotations

from typing import Iterable, Mapping

from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")


def _resolve_deployment_notes_field(settings: Mapping[str, object] | None) -> str:
    if not isinstance(settings, Mapping):
        return "deployment_notes"
    release_cfg = settings.get("release")
    if isinstance(release_cfg, Mapping):
        validation_cfg = release_cfg.get("validation_doc")
        if isinstance(validation_cfg, Mapping):
            field_id = validation_cfg.get("deployment_notes_field_id")
            if isinstance(field_id, str) and field_id.strip():
                return field_id.strip()
    return "deployment_notes"


def _extract_markdown(issue: Mapping[str, object], field_id: str) -> str:
    candidates: list[object] = []
    for key in (field_id, "deployment_notes"):
        if key in issue:
            candidates.append(issue[key])
    fields = issue.get("fields")
    if isinstance(fields, Mapping) and field_id in fields:
        candidates.append(fields[field_id])

    for candidate in candidates:
        if isinstance(candidate, Mapping):
            markdown = candidate.get("markdown")
            if isinstance(markdown, str):
                return markdown
            value = candidate.get("value")
            if isinstance(value, str):
                return value
        if isinstance(candidate, str):
            return candidate
    return ""


def _resolve_summary(issue: Mapping[str, object]) -> str:
    summary = issue.get("summary")
    if isinstance(summary, str):
        return summary
    fields = issue.get("fields")
    if isinstance(fields, Mapping):
        field_summary = fields.get("summary")
        if isinstance(field_summary, str):
            return field_summary
    return ""


def _resolve_url(issue: Mapping[str, object], base_url: str | None) -> str:
    for candidate in (issue.get("uri"), issue.get("url")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    key = issue.get("key") or issue.get("issue_key")
    if isinstance(key, str) and key and base_url:
        return f"{base_url.rstrip('/')}/browse/{key}"
    return key if isinstance(key, str) else ""


def build_validation_doc(
    *,
    issues: Iterable[Mapping[str, object]],
    settings: Mapping[str, object] | None,
    base_url: str | None,
) -> dict[str, object]:
    """Build the validation document payload without run metadata."""

    field_id = _resolve_deployment_notes_field(settings)
    items: list[dict[str, str]] = []
    for issue in issues:
        key = issue.get("key") or issue.get("issue_key")
        if not isinstance(key, str) or not key.strip():
            continue
        items.append(
            {
                "issue_key": key.strip(),
                "summary": _resolve_summary(issue),
                "deployment_notes": _extract_markdown(issue, field_id),
                "url": _resolve_url(issue, base_url),
            }
        )

    items.sort(key=lambda item: item["issue_key"])
    return {
        "deployment_notes_field_id": field_id,
        "items": items,
    }


__all__ = ["build_validation_doc", "PHOENIX_TZ"]
