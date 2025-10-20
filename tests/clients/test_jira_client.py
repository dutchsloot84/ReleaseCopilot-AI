from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Iterator

import pytest
import requests

from clients.jira_client import JiraClient
from releasecopilot.errors import JiraQueryError

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "jira"


def _load_response(name: str, *, status: int = 200) -> requests.Response:
    payload_path = FIXTURE_DIR / name
    response = requests.Response()
    response.status_code = status
    response._content = payload_path.read_bytes()
    response.headers["Content-Type"] = "application/json"
    response.url = "https://example.atlassian.net/rest/api/3/search"
    return response


@pytest.fixture()
def jira_client(tmp_path: Path) -> JiraClient:
    return JiraClient(
        base_url="https://example.atlassian.net",
        access_token="token",
        token_expiry=int(time.time()) + 3600,
        cache_dir=tmp_path,
    )


def test_fetch_issues_handles_pagination_and_caches(
    jira_client: JiraClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    responses: Iterator[requests.Response | Exception] = iter(
        [
            requests.Timeout("transient timeout"),
            _load_response("search_page1.json"),
            _load_response("search_page2.json"),
        ]
    )

    def _fake_request(method: str, url: str, **kwargs):
        payload = next(responses)
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(JiraClient, "_sleep", lambda _self, _seconds: None)
    monkeypatch.setattr(jira_client.session, "request", _fake_request)

    issues, cache_path = jira_client.fetch_issues(fix_version="Oct25")

    assert [issue["key"] for issue in issues] == ["APP-1", "APP-2", "APP-3"]
    assert cache_path is not None
    assert cache_path.exists()
    cache_contents = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache_contents["issues"][0]["key"] == "APP-1"


def test_fetch_issues_uses_cache_when_available(
    jira_client: JiraClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    cached_payload = {
        "issues": [
            {"key": "APP-99", "fields": {"summary": "Cached value"}},
        ],
    }
    jira_client._cache_response("jira_Oct25", cached_payload)

    def _should_not_be_called(*_args, **_kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("Network layer should not be invoked when cache is present")

    monkeypatch.setattr(jira_client, "_request_with_retry", _should_not_be_called)

    issues, cache_path = jira_client.fetch_issues(fix_version="Oct25", use_cache=True)

    assert [issue["key"] for issue in issues] == ["APP-99"]
    assert cache_path is not None
    assert cache_path.exists()


def test_fetch_issues_raises_on_http_error(
    jira_client: JiraClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure_response = _load_response("search_error.json", status=500)

    monkeypatch.setattr(jira_client.session, "request", lambda *args, **kwargs: failure_response)

    with pytest.raises(JiraQueryError) as exc:
        jira_client.fetch_issues(fix_version="Oct25")

    assert exc.value.context["status_code"] == 500
    assert exc.value.context["jql"].startswith("fixVersion = ")
