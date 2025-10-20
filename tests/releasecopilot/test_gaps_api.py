from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from releasecopilot.gaps.api import commits_without_story, stories_without_commits


def test_stories_without_commits_includes_metadata() -> None:
    payload = [{"key": "APP-7"}]
    response = stories_without_commits(
        payload,
        run_id="run-123",
        git_sha="abc123",
        args={"window_hours": 24},
        generated_at="2025-01-02T05:00:00",
    )

    assert response.run_id == "run-123"
    assert response.git_sha == "abc123"
    assert response.timezone == "America/Phoenix"
    assert response.generated_at == "2025-01-02T05:00:00-07:00"
    assert response.args == {"window_hours": 24}
    assert response.payload == payload


def test_commits_without_story_uses_current_time(monkeypatch) -> None:
    fixed = datetime(2025, 1, 2, 12, 30, tzinfo=ZoneInfo("America/Phoenix"))

    monkeypatch.setattr(
        "releasecopilot.gaps.api.datetime",
        type("_MockDateTime", (datetime,), {"now": classmethod(lambda cls, tz=None: fixed)}),
    )

    response = commits_without_story(
        [
            {"hash": "c1"},
        ],
        args={"window_hours": 12},
    )

    assert response.payload == [{"hash": "c1"}]
    assert response.args == {"window_hours": 12}
    assert response.timezone == "America/Phoenix"
    assert response.generated_at == "2025-01-02T12:30:00-07:00"
