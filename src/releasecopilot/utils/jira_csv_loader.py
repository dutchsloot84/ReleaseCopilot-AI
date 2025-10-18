"""Helpers for loading Jira issues from CSV exports."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Mapping


class JiraCSVLoaderError(RuntimeError):
    """Raised when CSV fallback files cannot be parsed."""


_KEY_ALIASES = {"issue key", "key"}
_SUMMARY_ALIASES = {"summary", "issue summary"}
_STATUS_ALIASES = {"status"}
_ASSIGNEE_ALIASES = {"assignee", "assignee name"}
_TYPE_ALIASES = {"issue type", "type"}


def _normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _build_field_map(fieldnames: Iterable[str]) -> Mapping[str, str]:
    mapping: dict[str, str] = {}
    for name in fieldnames:
        normalized = _normalize_header(name)
        mapping.setdefault(normalized, name)
    return mapping


def _resolve_column(field_map: Mapping[str, str], aliases: Iterable[str]) -> str | None:
    for alias in aliases:
        normalized = _normalize_header(alias)
        if normalized in field_map:
            return field_map[normalized]
    return None


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _build_issue(row: Mapping[str, Any], field_map: Mapping[str, str]) -> dict[str, Any]:
    key_column = _resolve_column(field_map, _KEY_ALIASES)
    summary_column = _resolve_column(field_map, _SUMMARY_ALIASES)
    if not key_column or not summary_column:
        missing = []
        if not key_column:
            missing.append("Issue key")
        if not summary_column:
            missing.append("Summary")
        raise JiraCSVLoaderError("CSV export is missing required columns: " + ", ".join(missing))

    key = _clean(row.get(key_column))
    summary = _clean(row.get(summary_column))
    if not key:
        raise JiraCSVLoaderError("CSV export row is missing an issue key")

    fields: dict[str, Any] = {"summary": summary}

    status_column = _resolve_column(field_map, _STATUS_ALIASES)
    if status_column:
        status_value = _clean(row.get(status_column))
        if status_value:
            fields["status"] = {"name": status_value}

    assignee_column = _resolve_column(field_map, _ASSIGNEE_ALIASES)
    if assignee_column:
        assignee_value = _clean(row.get(assignee_column))
        if assignee_value:
            fields["assignee"] = {"displayName": assignee_value}

    type_column = _resolve_column(field_map, _TYPE_ALIASES)
    if type_column:
        type_value = _clean(row.get(type_column))
        if type_value:
            fields["issuetype"] = {"name": type_value}

    return {"key": key, "fields": fields}


def load_issues_from_csv(path: Path) -> list[dict[str, Any]]:
    """Read Jira issues from ``path`` and return Jira-like issue payloads."""

    if not path.exists() or not path.is_file():
        raise JiraCSVLoaderError(f"CSV file not found: {path}")

    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise JiraCSVLoaderError("CSV file has no header row")
            field_map = _build_field_map(reader.fieldnames)
            issues = []
            for row in reader:
                if not any(value for value in row.values()):
                    continue
                issue = _build_issue(row, field_map)
                issues.append(issue)
    except UnicodeDecodeError as exc:  # pragma: no cover - defensive guard
        raise JiraCSVLoaderError("CSV file must be UTF-8 encoded") from exc
    except csv.Error as exc:
        raise JiraCSVLoaderError("CSV file is malformed") from exc

    issues.sort(key=lambda issue: issue.get("key", ""))
    return issues


__all__ = ["JiraCSVLoaderError", "load_issues_from_csv"]
