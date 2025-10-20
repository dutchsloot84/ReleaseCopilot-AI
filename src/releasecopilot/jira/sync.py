"""Synchronization helpers for Jira webhook deliveries."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from matcher import engine
from releasecopilot.logging_config import get_correlation_id

from .webhook_parser import JiraWebhookEvent

ARTIFACT_DIR = Path("artifacts/issues/wave3/jira_webhook")


def phoenix_now() -> datetime:
    """Return the current datetime in the America/Phoenix timezone."""

    return datetime.now(ZoneInfo("America/Phoenix"))


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip()


def _artifact_path(prefix: str | None = None) -> Path:
    timestamp = phoenix_now().strftime("%Y%m%dT%H%M%S")
    filename = f"{timestamp}-{prefix or 'batch'}.json"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_DIR / filename


def recompute_correlation(
    *,
    events: Sequence[JiraWebhookEvent] | Iterable[JiraWebhookEvent],
    match=engine.match,
) -> Mapping[str, Any]:
    """Run correlation for touched issues and persist Phoenix metadata."""

    event_list = list(events)
    if not event_list:
        return {}

    issue_keys = sorted({event.issue_key for event in event_list})
    issues = [{"issue_key": key} for key in issue_keys]
    matched, missing, orphans, summary = match(issues=issues, commits=[])

    phoenix_timestamp = phoenix_now().isoformat(timespec="seconds")
    payload: dict[str, Any] = {
        "run_id": get_correlation_id(),
        "git_sha": _git_sha(),
        "generated_at": phoenix_timestamp,
        "timezone": "America/Phoenix",
        "issues": [
            {
                "issue_key": event.issue_key,
                "updated_at": event.updated_at,
                "phoenix_updated_at": event.phoenix_timestamp,
                "event_type": event.event_type,
            }
            for event in event_list
        ],
        "correlation": {
            "matched": matched,
            "missing": missing,
            "orphans": orphans,
            "summary": summary,
        },
    }

    artifact = _artifact_path(prefix="-".join(issue_keys))
    artifact.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return {"artifact_path": str(artifact), "issues": issue_keys, "summary": summary}


__all__ = ["recompute_correlation", "phoenix_now"]
