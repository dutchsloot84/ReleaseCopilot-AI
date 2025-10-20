"""Story link resolution helpers for matcher workflows."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

STORY_KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")


def _normalize_source(text: str | None) -> str | None:
    if not text:
        return None
    if not isinstance(text, str):  # defensive - tolerate unexpected types
        return None
    normalized = text.strip()
    if not normalized:
        return None
    return normalized.upper()


def parse_story_keys(source: str | None) -> list[str]:
    """Return all story keys found in *source* preserving order."""

    normalized = _normalize_source(source)
    if not normalized:
        return []
    matches = STORY_KEY_RE.findall(normalized)
    seen: list[str] = []
    for match in matches:
        if match not in seen:
            seen.append(match)
    return seen


def extract_story_keys(
    *,
    message: str | None,
    branch: str | None,
    pr_title: str | None,
) -> tuple[str, ...]:
    """Return unique story keys preferring commit message, branch, then PR title."""

    ordered: list[str] = []
    for source in (message, branch, pr_title):
        for match in parse_story_keys(source):
            if match not in ordered:
                ordered.append(match)
    return tuple(ordered)


def _pull_request_title(commit: Mapping[str, Any]) -> str | None:
    pr_title = commit.get("pr_title")
    if isinstance(pr_title, str) and pr_title.strip():
        return pr_title
    pull_request = commit.get("pull_request")
    if isinstance(pull_request, Mapping):
        title = pull_request.get("title")
        if isinstance(title, str) and title.strip():
            return title
    metadata = commit.get("metadata")
    if isinstance(metadata, Mapping):
        title = metadata.get("pr_title") or metadata.get("pull_request_title")
        if isinstance(title, str) and title.strip():
            return title
    return None


def story_keys_from_commit(commit: Mapping[str, Any]) -> tuple[str, ...]:
    """Resolve story keys for a commit respecting message/branch/title precedence."""

    raw_keys = commit.get("story_keys")
    if isinstance(raw_keys, (list, tuple)):
        ordered: list[str] = []
        for item in raw_keys:
            if isinstance(item, str):
                for match in parse_story_keys(item):
                    if match not in ordered:
                        ordered.append(match)
        if ordered:
            return tuple(ordered)

    message = commit.get("message") or commit.get("summary")
    branch = commit.get("branch")
    title = _pull_request_title(commit)
    return extract_story_keys(message=message, branch=branch, pr_title=title)


__all__ = [
    "STORY_KEY_RE",
    "extract_story_keys",
    "parse_story_keys",
    "story_keys_from_commit",
]
