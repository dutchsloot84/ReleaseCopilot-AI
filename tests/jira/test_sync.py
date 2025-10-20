from __future__ import annotations

from pathlib import Path

import json

import pytest

from releasecopilot.jira.sync import ARTIFACT_DIR, recompute_correlation
from releasecopilot.jira.webhook_parser import JiraWebhookEvent


@pytest.fixture(autouse=True)
def _clean_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_COMMITTER_NAME", "test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.com")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    yield


def _event(issue_key: str) -> JiraWebhookEvent:
    return JiraWebhookEvent(
        event_type="jira:issue_updated",
        issue_key=issue_key,
        issue_id=f"{issue_key}-id",
        updated_at="2024-01-01T00:00:00Z",
        issue={"key": issue_key, "fields": {}},
        fields={},
        changelog={},
        delivery_id="delivery",
        timestamp="2024-01-01T00:00:00Z",
        payload={"webhookEvent": "jira:issue_updated"},
    )


def test_recompute_correlation_writes_artifact(monkeypatch: pytest.MonkeyPatch):
    written = {}

    def _match(**kwargs):
        written.update(kwargs)
        return [], [], [], {"total_issues": 1}

    result = recompute_correlation(events=[_event("MOB-1")], match=_match)
    assert result["issues"] == ["MOB-1"]
    assert written["issues"] == [{"issue_key": "MOB-1"}]

    artifacts = sorted(ARTIFACT_DIR.glob("*.json"))
    assert artifacts, "Expected artifact file"
    payload = json.loads(artifacts[0].read_text())
    assert payload["timezone"] == "America/Phoenix"
    assert payload["issues"][0]["phoenix_updated_at"].endswith("-07:00")
