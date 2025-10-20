import json
from pathlib import Path
from typing import Any, Dict

import pytest

from scripts.github import ci_watchdog

FIXTURES = Path(__file__).parent.parent / "fixtures" / "github" / "watchdog"


class DummyResponse:
    def __init__(self, payload: Any):
        self._payload = payload
        self.status_code = 200
        self.links: Dict[str, Dict[str, str]] = {}

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, mapping: Dict[str, Any]):
        self.headers: Dict[str, str] = {}
        self._mapping = mapping

    def get(self, url: str, params=None):
        key = url
        if params:
            key = f"{url}?{json.dumps(params, sort_keys=True)}"
        if key not in self._mapping:
            raise AssertionError(f"Unexpected URL requested: {key}")
        return DummyResponse(self._mapping[key])


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def mock_session(monkeypatch: pytest.MonkeyPatch, mapping: Dict[str, Any]):
    def _session():
        return DummySession(mapping)

    monkeypatch.setenv("ORCHESTRATOR_BOT_TOKEN", "test-token")
    monkeypatch.setattr(ci_watchdog.requests, "Session", _session)


def freeze_utc_now(monkeypatch: pytest.MonkeyPatch, when):
    class FrozenDateTime(ci_watchdog._dt.datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return when
            return when.astimezone(tz)

    monkeypatch.setattr(ci_watchdog._dt, "datetime", FrozenDateTime)


def test_collect_failures_filters_and_sorts(monkeypatch):
    mapping = {
        'https://api.github.com/repos/example/repo/pulls?{"direction": "desc", "per_page": "50", "sort": "updated", "state": "open"}': load_fixture(
            "pulls.json"
        ),
        "https://api.github.com/repos/example/repo/commits/abc123/check-runs": load_fixture(
            "check_runs_abc123.json"
        ),
    }
    freeze_utc_now(
        monkeypatch,
        ci_watchdog._dt.datetime(2024, 5, 1, 14, 0, tzinfo=ci_watchdog._dt.timezone.utc),
    )
    mock_session(monkeypatch, mapping)

    failures = ci_watchdog.collect_failures("example/repo", max_age_hours=72)
    assert len(failures) == 1
    failure = failures[0]
    assert failure.number == 42
    assert failure.failing_checks[0].name == "pytest"


def test_collect_failures_skips_stale(monkeypatch):
    mapping = {
        'https://api.github.com/repos/example/repo/pulls?{"direction": "desc", "per_page": "50", "sort": "updated", "state": "open"}': load_fixture(
            "pulls.json"
        ),
        "https://api.github.com/repos/example/repo/commits/abc123/check-runs": load_fixture(
            "check_runs_stale.json"
        ),
    }
    freeze_utc_now(
        monkeypatch,
        ci_watchdog._dt.datetime(2024, 5, 1, 14, 0, tzinfo=ci_watchdog._dt.timezone.utc),
    )
    mock_session(monkeypatch, mapping)

    failures = ci_watchdog.collect_failures("example/repo", max_age_hours=24)
    assert failures == []


def test_render_report_matches_golden(monkeypatch, tmp_path):
    freeze_utc_now(
        monkeypatch,
        ci_watchdog._dt.datetime(2024, 5, 1, 14, 0, tzinfo=ci_watchdog._dt.timezone.utc),
    )

    failure = ci_watchdog.PullRequestFailure(
        number=42,
        title="Fix failing tests",
        html_url="https://github.com/example/repo/pull/42",
        head_sha="abc123",
        latest_failure_at="2024-05-01T13:00:00Z",
        failing_checks=(
            ci_watchdog.FailingCheck(
                name="pytest",
                conclusion="failure",
                completed_at="2024-05-01T13:00:00Z",
                html_url="https://github.com/example/repo/runs/1",
            ),
        ),
    )

    report = ci_watchdog.render_report([failure])
    golden = (Path(__file__).parent.parent / "golden" / "watchdog" / "report.md").read_text(
        encoding="utf-8"
    )
    assert report == golden


def test_should_autofix_gating(monkeypatch):
    event = {
        "comment": {"body": "/watchdog autofix", "author_association": "MEMBER"},
        "issue": {"pull_request": {"url": ""}, "labels": [{"name": "automation"}]},
        "pull_request": {"approved_review_count": 1},
    }
    assert ci_watchdog.should_autofix(event) is True


def test_should_autofix_rejects_without_approval(monkeypatch):
    event = {
        "comment": {"body": "/watchdog autofix", "author_association": "MEMBER"},
        "issue": {"pull_request": {"url": ""}, "labels": [{"name": "automation"}]},
        "pull_request": {"reviews": [{"state": "COMMENTED"}]},
    }
    assert ci_watchdog.should_autofix(event) is False
