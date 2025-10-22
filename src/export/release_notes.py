"""Helpers for building grouped release notes payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping


@dataclass(slots=True)
class ReleaseNote:
    """Immutable representation of a single release note entry."""

    issue_key: str
    summary: str
    change_type: str
    url: str

    def as_dict(self) -> dict[str, str]:
        return {
            "issue_key": self.issue_key,
            "summary": self.summary,
            "change_type": self.change_type,
            "url": self.url,
        }


def _derive_change_type(issue: Mapping[str, object]) -> str:
    candidates = (
        issue.get("issue_type"),
        issue.get("type"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    labels = issue.get("labels")
    if isinstance(labels, (list, tuple)):
        for label in labels:
            if isinstance(label, str) and label.strip():
                return label.strip()

    fields = issue.get("fields")
    if isinstance(fields, Mapping):
        field_type = fields.get("issuetype")
        if isinstance(field_type, Mapping):
            name = field_type.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return "Uncategorized"


def _resolve_summary(issue: Mapping[str, object]) -> str:
    summary = issue.get("summary")
    if isinstance(summary, str):
        return summary
    fields = issue.get("fields")
    if isinstance(fields, Mapping):
        summary_value = fields.get("summary")
        if isinstance(summary_value, str):
            return summary_value
    return ""


def _resolve_url(issue: Mapping[str, object], base_url: str | None) -> str:
    url_candidates = (
        issue.get("uri"),
        issue.get("url"),
        issue.get("browse_url"),
    )
    for candidate in url_candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate

    key_candidate = issue.get("key") or issue.get("issue_key")
    if isinstance(key_candidate, str) and key_candidate and base_url:
        sanitized = base_url.rstrip("/")
        return f"{sanitized}/browse/{key_candidate}"
    return key_candidate if isinstance(key_candidate, str) else ""


def group_release_notes(
    issues: Iterable[Mapping[str, object]],
    *,
    base_url: str | None = None,
) -> dict[str, list[ReleaseNote]]:
    """Group normalized issues into release note buckets."""

    grouped: MutableMapping[str, list[ReleaseNote]] = {}
    for issue in issues:
        key = issue.get("key") or issue.get("issue_key")
        if not isinstance(key, str) or not key.strip():
            continue

        note = ReleaseNote(
            issue_key=key.strip(),
            summary=_resolve_summary(issue),
            change_type=_derive_change_type(issue),
            url=_resolve_url(issue, base_url),
        )
        bucket = grouped.setdefault(note.change_type, [])
        bucket.append(note)

    for notes in grouped.values():
        notes.sort(key=lambda value: value.issue_key)

    return dict(grouped)


def serialise_grouped_notes(grouped: Mapping[str, Iterable[ReleaseNote]]) -> dict[str, list[dict[str, str]]]:
    """Convert grouped notes into JSON-friendly dictionaries."""

    output: dict[str, list[dict[str, str]]] = {}
    for change_type, notes in grouped.items():
        output[change_type] = [note.as_dict() for note in notes]
    return output


def flatten_grouped_notes(grouped: Mapping[str, Iterable[ReleaseNote]]) -> list[dict[str, str]]:
    """Generate a flat list of notes annotated with change type for tabular exports."""

    rows: list[dict[str, str]] = []
    for change_type, notes in grouped.items():
        for note in notes:
            rows.append({
                "change_type": change_type,
                "issue_key": note.issue_key,
                "summary": note.summary,
                "url": note.url,
            })
    return rows


__all__ = [
    "ReleaseNote",
    "group_release_notes",
    "serialise_grouped_notes",
    "flatten_grouped_notes",
]
