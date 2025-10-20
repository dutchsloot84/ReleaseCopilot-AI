from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

from clients.bitbucket_client import BitbucketClient
import pytest
import requests

from releasecopilot.errors import BitbucketRequestError

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "bitbucket"


def _load_response(name: str, *, status: int = 200) -> requests.Response:
    payload_path = FIXTURE_DIR / name
    response = requests.Response()
    response.status_code = status
    response._content = payload_path.read_bytes()
    response.headers["Content-Type"] = "application/json"
    response.url = "https://api.bitbucket.org/2.0/repositories/example/repo/commits"
    return response


@pytest.fixture()
def bitbucket_client(tmp_path: Path) -> BitbucketClient:
    return BitbucketClient(workspace="example", cache_dir=tmp_path)


def test_fetch_commits_for_branch_paginates_and_retries(
    bitbucket_client: BitbucketClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    responses: Iterator[requests.Response | Exception] = iter(
        [
            requests.Timeout("retry please"),
            _load_response("commits_page1.json"),
            _load_response("commits_page2.json"),
        ]
    )

    def _fake_request(method: str, url: str, **kwargs):
        payload = next(responses)
        if isinstance(payload, Exception):
            raise payload
        return payload

    monkeypatch.setattr(BitbucketClient, "_sleep", lambda _self, _seconds: None)
    monkeypatch.setattr(bitbucket_client.session, "request", _fake_request)

    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 3)

    commits = bitbucket_client._fetch_commits_for_branch("repo", "main", start, end)

    hashes = [commit["hash"] for commit in commits]
    assert hashes == ["abc123", "def456"]
    assert all(commit["repository"] == "repo" for commit in commits)
    assert all(commit["branch"] == "main" for commit in commits)


def test_fetch_commits_raises_on_http_error(
    bitbucket_client: BitbucketClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = _load_response("commits_error.json", status=500)

    monkeypatch.setattr(bitbucket_client.session, "request", lambda *args, **kwargs: failure)

    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 3)

    with pytest.raises(BitbucketRequestError) as exc:
        bitbucket_client._fetch_commits_for_branch("repo", "main", start, end)

    assert exc.value.context["status_code"] == 500
    assert exc.value.context["repository"] == "repo"


def test_fetch_commits_uses_cache_when_requested(
    bitbucket_client: BitbucketClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 3)
    cache_key = "bitbucket_repo_main_20240101_20240103"
    cached_payload = {
        "values": [
            {
                "hash": "cached123",
                "message": "Cached commit",
                "repository": "repo",
                "branch": "main",
            }
        ]
    }
    bitbucket_client._cache_response(cache_key, cached_payload)

    def _should_not_be_called(*_args, **_kwargs):  # pragma: no cover - defensive guard
        raise AssertionError("Network layer should not be invoked when cache is present")

    monkeypatch.setattr(bitbucket_client, "_fetch_commits_for_branch", _should_not_be_called)

    commits, cache_keys = bitbucket_client.fetch_commits(
        repositories=["repo"],
        branches=["main"],
        start=start,
        end=end,
        use_cache=True,
    )

    assert [commit["hash"] for commit in commits] == ["cached123"]
    assert cache_keys == [cache_key]
