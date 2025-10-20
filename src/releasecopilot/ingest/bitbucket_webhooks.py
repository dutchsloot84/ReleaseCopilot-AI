"""Webhook normalisation for Bitbucket events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from processors.audit_processor import STORY_KEY_RE

from releasecopilot.logging_config import get_logger

from .bitbucket_scanner import PHOENIX_TZ
from .storage import CommitStorage, CommitUpsert

LOGGER = get_logger(__name__)
SUPPORTED_EVENTS = {
    "repo:push",
    "pullrequest:created",
    "pullrequest:updated",
    "pullrequest:fulfilled",
}


def _header(headers: Mapping[str, Any] | None, key: str) -> str | None:
    if not headers:
        return None
    target = key.lower()
    for header, value in headers.items():
        if header.lower() == target and isinstance(value, str):
            return value
    return None


def extract_story_keys(
    message: str | None,
    branch: str | None = None,
    pr_title: str | None = None,
) -> tuple[str, ...]:
    """Return unique story keys preferring message > branch > PR title."""

    ordered: list[str] = []
    for source in (message, branch, pr_title):
        if not source:
            continue
        matches = STORY_KEY_RE.findall(source.upper())
        for match in matches:
            if match not in ordered:
                ordered.append(match)
    return tuple(ordered)


def _normalize_files(entries: Iterable[Mapping[str, Any]] | None) -> tuple[str, ...]:
    if not entries:
        return tuple()
    paths = []
    for entry in entries:
        path = entry.get("path") if isinstance(entry, Mapping) else None
        if isinstance(path, str):
            paths.append(path)
    seen: list[str] = []
    for path in paths:
        if path not in seen:
            seen.append(path)
    return tuple(seen)


def _authorship(commit: Mapping[str, Any]) -> str | None:
    author = commit.get("author")
    if not isinstance(author, Mapping):
        return None
    raw = author.get("raw")
    if isinstance(raw, str) and raw:
        return raw
    user = author.get("user")
    if isinstance(user, Mapping):
        display = user.get("display_name")
        if isinstance(display, str) and display:
            return display
    return None


def handle_push(event: Mapping[str, Any]) -> list[CommitUpsert]:
    """Normalize Bitbucket push payloads for idempotent storage."""

    repository = _resolve_repository(event)
    commits: list[CommitUpsert] = []
    seen: set[str] = set()
    push = event.get("push") or {}
    for change in push.get("changes", []):
        if not isinstance(change, Mapping):
            continue
        branch = _resolve_branch(change)
        for commit in change.get("commits", []):
            if not isinstance(commit, Mapping):
                continue
            commit_hash = commit.get("hash")
            if not isinstance(commit_hash, str) or not commit_hash:
                continue
            if commit_hash in seen:
                continue
            seen.add(commit_hash)
            story_keys = extract_story_keys(commit.get("message"), branch)
            commits.append(
                CommitUpsert(
                    hash=commit_hash,
                    repository=repository,
                    authorship=_authorship(commit),
                    files_changed=_normalize_files(commit.get("files")),
                    story_keys=story_keys,
                    source="webhook",
                    branch=branch,
                    modified_on=commit.get("date") or commit.get("timestamp"),
                )
            )
    return commits


def _resolve_branch(change: Mapping[str, Any]) -> str | None:
    for key in ("new", "old"):
        pointer = change.get(key)
        if isinstance(pointer, Mapping):
            name = pointer.get("name")
            if isinstance(name, str) and name:
                return name
    return None


def _resolve_repository(event: Mapping[str, Any]) -> str:
    repository = event.get("repository") or {}
    if isinstance(repository, Mapping):
        for key in ("full_name", "name", "slug"):
            value = repository.get(key)
            if isinstance(value, str) and value:
                return value
    return "unknown"


def handle_pull_request(event: Mapping[str, Any]) -> list[CommitUpsert]:
    """Handle Bitbucket pull request webhook payloads."""

    repository = _resolve_repository(event)
    pull_request = event.get("pullrequest") or {}
    if not isinstance(pull_request, Mapping):
        pull_request = {}

    branch = (
        ((pull_request.get("source") or {}).get("branch") or {}).get("name")
        if isinstance(pull_request.get("source"), Mapping)
        else None
    )
    if not isinstance(branch, str):
        branch = None

    title = pull_request.get("title") if isinstance(pull_request, Mapping) else None
    if not isinstance(title, str):
        title = None

    commits_payload = pull_request.get("commits")
    commits: list[CommitUpsert] = []
    seen: set[str] = set()
    if isinstance(commits_payload, Sequence):
        iterable: Iterable[Any] = commits_payload
    else:
        iterable = []
    for commit in iterable:
        if not isinstance(commit, Mapping):
            continue
        commit_hash = commit.get("hash") or commit.get("id")
        if not isinstance(commit_hash, str) or not commit_hash:
            continue
        if commit_hash in seen:
            continue
        seen.add(commit_hash)
        story_keys = extract_story_keys(commit.get("message"), branch, title)
        commits.append(
            CommitUpsert(
                hash=commit_hash,
                repository=repository,
                authorship=_authorship(commit),
                files_changed=_normalize_files(commit.get("files")),
                story_keys=story_keys,
                source="webhook",
                branch=branch,
                modified_on=commit.get("date") or commit.get("timestamp"),
            )
        )
    return commits


class BitbucketWebhookHandler:
    """Process Bitbucket webhook events and persist commit metadata."""

    def __init__(
        self,
        *,
        storage: CommitStorage,
        secret: str | None = None,
        tz: ZoneInfo | None = None,
    ) -> None:
        self.storage = storage
        self.secret = secret
        self.tz = tz or PHOENIX_TZ

    def process(
        self,
        payload: Mapping[str, Any],
        headers: Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        if self.secret:
            provided = _header(headers, "X-Webhook-Secret")
            if provided != self.secret:
                LOGGER.warning("Bitbucket webhook rejected due to secret mismatch")
                return 401, {"ok": False, "reason": "unauthorized"}

        event_key = _resolve_event_key(payload)
        if event_key not in SUPPORTED_EVENTS:
            LOGGER.info(
                "Ignoring unsupported Bitbucket event",
                extra={"event_key": event_key},
            )
            return 202, {"ok": True, "ingested": 0, "ignored": True, "event_key": event_key}

        if event_key == "repo:push":
            commits = handle_push(payload)
        else:
            commits = handle_pull_request(payload)

        if not commits:
            LOGGER.info(
                "No commits extracted from webhook",
                extra={"event_key": event_key},
            )
            return 202, {"ok": True, "ingested": 0}

        observed = datetime.now(tz=self.tz)
        self.storage.upsert_many(commits, observed_at=observed)
        return 202, {"ok": True, "ingested": len(commits)}


def _resolve_event_key(payload: Mapping[str, Any]) -> str:
    for key in ("event_key", "eventKey", "event", "eventType"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return "unknown"
