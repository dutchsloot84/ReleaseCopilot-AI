"""Normalize Atlassian Jira webhook payloads into deterministic models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping
from zoneinfo import ZoneInfo


def _parse_timestamp(value: Any) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, (int, float)):
        # Atlassian timestamps are expressed in milliseconds
        return (
            datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    text = str(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class JiraWebhookEvent:
    """Normalized view of a Jira webhook delivery."""

    event_type: str
    issue_key: str
    issue_id: str
    updated_at: str
    issue: Mapping[str, Any]
    fields: Mapping[str, Any]
    changelog: Mapping[str, Any]
    delivery_id: str | None
    timestamp: str | None
    payload: Mapping[str, Any]

    @property
    def issue_keys(self) -> tuple[str, ...]:
        return (self.issue_key,)

    @property
    def phoenix_timestamp(self) -> str:
        dt = datetime.fromisoformat(self.updated_at.replace("Z", "+00:00"))
        phoenix = dt.astimezone(ZoneInfo("America/Phoenix"))
        return phoenix.isoformat(timespec="seconds")


def normalize_payload(event: Mapping[str, Any]) -> JiraWebhookEvent:
    """Return a ``JiraWebhookEvent`` from the raw webhook payload."""

    mutable_event: MutableMapping[str, Any] = dict(event)
    event_type = str(mutable_event.get("webhookEvent") or "").strip()
    if not event_type:
        raise ValueError("Missing webhookEvent")

    issue_payload = mutable_event.get("issue")
    if not isinstance(issue_payload, Mapping):
        raise ValueError("Missing issue payload")

    issue_key = str(issue_payload.get("key") or issue_payload.get("id") or "").strip()
    if not issue_key:
        raise ValueError("Missing issue key")

    issue_id = str(issue_payload.get("id") or issue_key)
    fields = issue_payload.get("fields")
    if not isinstance(fields, Mapping):
        fields = {}

    updated_source = (
        fields.get("updated")
        or fields.get("created")
        or mutable_event.get("timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    updated_at = _parse_timestamp(updated_source)

    delivery_id: str | None = None
    for key in ("deliveryId", "delivery_id", "eventId", "event_id"):
        candidate = mutable_event.get(key)
        if candidate:
            delivery_id = str(candidate)
            break

    changelog = mutable_event.get("changelog")
    if not isinstance(changelog, Mapping):
        changelog = {}

    timestamp_value = mutable_event.get("timestamp")
    timestamp = _parse_timestamp(timestamp_value) if timestamp_value is not None else None

    return JiraWebhookEvent(
        event_type=event_type,
        issue_key=issue_key,
        issue_id=issue_id,
        updated_at=updated_at,
        issue=issue_payload,
        fields=fields,
        changelog=changelog,
        delivery_id=delivery_id,
        timestamp=timestamp,
        payload=mutable_event,
    )


__all__ = ["JiraWebhookEvent", "normalize_payload"]
