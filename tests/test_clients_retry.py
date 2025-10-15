from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Iterable

import pytest
import requests

from clients.bitbucket_client import BitbucketClient
from clients.jira_client import JiraClient
from releasecopilot.errors import BitbucketRequestError, JiraQueryError


class DummyResponse:
    def __init__(
        self,
        status_code: int,
        json_data: dict[str, Any] | None = None,
        *,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


class FakeSession:
    def __init__(self, responses: list[DummyResponse]) -> None:
        self._responses = responses

    def request(self, method: str, url: str, **_: Any) -> DummyResponse:
        if not self._responses:
            raise AssertionError("No more responses configured")
        return self._responses.pop(0)


class ZeroJitter:
    def uniform(self, _: float, __: float) -> float:  # noqa: D401
        return 0.0


@pytest.fixture(autouse=True)
def reset_logging_handlers() -> None:
    # Ensure each test starts from a clean logging configuration
    from releasecopilot.logging_config import configure_logging

    configure_logging("CRITICAL")


def test_jira_fetch_retries_on_rate_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    responses = [
        DummyResponse(
            429,
            text="Too many requests",
            headers={"Retry-After": "1", "X-RateLimit-Remaining": "0"},
        ),
        DummyResponse(
            200,
            json_data={"issues": [], "total": 0},
            headers={"X-RateLimit-Remaining": "98"},
        ),
    ]
    client = JiraClient(
        base_url="https://example.atlassian.net",
        access_token="token",
        token_expiry=int(time.time()) + 3600,
        cache_dir=str(tmp_path),
    )
    client.session = FakeSession(responses)  # type: ignore[assignment]
    client._random = ZeroJitter()
    delays: list[float] = []
    monkeypatch.setattr(
        JiraClient, "_sleep", lambda self, seconds: delays.append(seconds)
    )

    caplog.set_level("DEBUG")
    issues, _ = client.fetch_issues(fix_version="1.0.0")

    assert issues == []
    assert delays and delays[0] >= 1
    retry_logs = [
        record
        for record in caplog.records
        if record.levelname == "WARNING"
        and record.getMessage() == "Retrying after status"
    ]
    assert retry_logs
    assert getattr(retry_logs[0], "status_code") == 429


def test_jira_fetch_issues_raises_typed_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    responses = [DummyResponse(500, json_data={}, text="server down") for _ in range(5)]
    client = JiraClient(
        base_url="https://example.atlassian.net",
        access_token="token",
        token_expiry=int(time.time()) + 3600,
        cache_dir=str(tmp_path),
    )
    client.session = FakeSession(responses)  # type: ignore[assignment]
    client._random = ZeroJitter()
    delays: list[float] = []
    monkeypatch.setattr(
        JiraClient, "_sleep", lambda self, seconds: delays.append(seconds)
    )

    caplog.set_level("ERROR")
    with pytest.raises(JiraQueryError) as excinfo:
        client.fetch_issues(fix_version="2.0.0")

    assert excinfo.value.context["status_code"] == 500
    assert "server down" in excinfo.value.context["snippet"]
    assert len(delays) == client._MAX_ATTEMPTS - 1
    assert any(record.getMessage() == "Jira search failed" for record in caplog.records)


def test_bitbucket_retries_and_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    now = datetime.utcnow()
    responses = [
        DummyResponse(429, text="rate limit", headers={"Retry-After": "1"}),
        DummyResponse(200, json_data={"values": [{"hash": "abc"}], "next": None}),
    ]
    client = BitbucketClient(workspace="workspace", cache_dir=str(tmp_path))
    client.session = FakeSession(responses)  # type: ignore[assignment]
    client._random = ZeroJitter()
    delays: list[float] = []
    monkeypatch.setattr(
        BitbucketClient, "_sleep", lambda self, seconds: delays.append(seconds)
    )

    caplog.set_level("DEBUG")
    commits, _ = client.fetch_commits(
        repositories=["repo"],
        branches=["main"],
        start=now - timedelta(days=1),
        end=now,
    )

    assert commits and commits[0]["hash"] == "abc"
    assert delays and delays[0] >= 1
    assert any(record.getMessage() == "HTTP request" for record in caplog.records)
    assert any(
        record.getMessage() == "HTTP response"
        and getattr(record, "repository", None) == "repo"
        for record in caplog.records
    )


def test_bitbucket_raises_typed_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    now = datetime.utcnow()
    responses = [DummyResponse(503, text="service unavailable") for _ in range(5)]
    client = BitbucketClient(workspace="workspace", cache_dir=str(tmp_path))
    client.session = FakeSession(responses)  # type: ignore[assignment]
    client._random = ZeroJitter()
    delays: list[float] = []
    monkeypatch.setattr(
        BitbucketClient, "_sleep", lambda self, seconds: delays.append(seconds)
    )

    caplog.set_level("ERROR")
    with pytest.raises(BitbucketRequestError) as excinfo:
        client.fetch_commits(
            repositories=["repo"],
            branches=["main"],
            start=now - timedelta(days=1),
            end=now,
        )

    assert excinfo.value.context["status_code"] == 503
    assert "service unavailable" in excinfo.value.context["snippet"]
    assert len(delays) == client._MAX_ATTEMPTS - 1
    assert any(
        record.getMessage() == "Bitbucket HTTP error" for record in caplog.records
    )


def test_retries_can_be_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    monkeypatch.setenv("RC_DISABLE_RETRIES", "true")
    client = JiraClient(
        base_url="https://example.atlassian.net",
        access_token="token",
        token_expiry=int(time.time()) + 3600,
        cache_dir=str(tmp_path),
    )
    client.session = FakeSession([DummyResponse(500, text="error")])  # type: ignore[assignment]
    client._random = ZeroJitter()
    calls: list[float] = []
    monkeypatch.setattr(
        JiraClient, "_sleep", lambda self, seconds: calls.append(seconds)
    )

    with pytest.raises(JiraQueryError):
        client.fetch_issues(fix_version="no-retry")

    assert not calls


def test_run_audit_uses_injected_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    import importlib
    import sys

    fake_config = ModuleType("config")
    fake_settings = ModuleType("config.settings")
    fake_settings.load_settings = lambda overrides=None: {}
    fake_config.settings = fake_settings

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    monkeypatch.setitem(sys.modules, "config", fake_config)
    monkeypatch.setitem(sys.modules, "config.settings", fake_settings)
    importlib.invalidate_caches()
    main = importlib.import_module("main")

    class DummyIssueProvider:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def fetch_issues(
            self, *, fix_version: str, use_cache: bool = False
        ) -> tuple[list[dict[str, Any]], Path]:
            self.calls.append({"fix_version": fix_version, "use_cache": use_cache})
            cache_path = tmp_path / "issue-cache.json"
            cache_path.write_text("{}", encoding="utf-8")
            return ([{"key": "ISSUE-1"}]), cache_path

    class DummyCommitProvider:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []
            self._cache_files: dict[str, Path] = {}

        def fetch_commits(
            self,
            *,
            repositories: Iterable[str],
            branches: Iterable[str],
            start: datetime,
            end: datetime,
            use_cache: bool = False,
        ) -> tuple[list[dict[str, Any]], list[str]]:
            payload = {
                "repositories": list(repositories),
                "branches": list(branches),
                "start": start,
                "end": end,
                "use_cache": use_cache,
            }
            self.calls.append(payload)
            cache_key = "dummy-cache"
            cache_path = tmp_path / "commit-cache.json"
            cache_path.write_text("{}", encoding="utf-8")
            self._cache_files[cache_key] = cache_path
            commit = {
                "hash": "abc123",
                "repository": payload["repositories"][0],
                "branch": payload["branches"][0],
            }
            return [commit], [cache_key]

        def get_last_cache_file(self, name: str) -> Path | None:
            return self._cache_files.get(name)

    data_dir = tmp_path / "data"
    temp_dir = tmp_path / "temp"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "TEMP_DIR", temp_dir)

    settings = {
        "aws": {"region": "us-east-1"},
        "storage": {"s3": {}, "dynamodb": {"jira_issue_table": "table"}},
        "bitbucket": {
            "workspace": "workspace",
            "default_branches": ["main"],
            "repositories": ["repo"],
            "credentials": {},
        },
        "jira": {"base_url": "https://example", "credentials": {}},
    }

    monkeypatch.setattr(main, "load_settings", lambda overrides=None: settings)

    def fail_build_jira_store(_: Any) -> None:
        raise AssertionError("build_jira_store should not be called")

    def fail_build_bitbucket(_: Any) -> None:
        raise AssertionError("build_bitbucket_client should not be called")

    monkeypatch.setattr(main, "build_jira_store", fail_build_jira_store)
    monkeypatch.setattr(main, "build_bitbucket_client", fail_build_bitbucket)

    class DummyAuditProcessor:
        def __init__(
            self, *, issues: list[dict[str, Any]], commits: list[dict[str, Any]]
        ) -> None:
            self._issues = issues
            self._commits = commits

        def process(self) -> SimpleNamespace:
            return SimpleNamespace(
                summary={"issues": len(self._issues), "commits": len(self._commits)},
                stories_with_no_commits=[],
                orphan_commits=[],
                commit_story_mapping=[],
            )

    class DummyExcelExporter:
        def __init__(self, output_dir: Path) -> None:
            self.output_dir = output_dir
            self.output_dir.mkdir(parents=True, exist_ok=True)

        def export(self, data: dict[str, Any], filename: str) -> Path:
            path = self.output_dir / filename
            path.write_text("excel", encoding="utf-8")
            return path

    monkeypatch.setattr(main, "AuditProcessor", DummyAuditProcessor)
    monkeypatch.setattr(main, "ExcelExporter", DummyExcelExporter)

    uploads: dict[str, Any] = {}

    def capture_uploads(
        *,
        config: Any,
        settings: dict[str, Any],
        reports: Iterable[Path],
        raw_files: Iterable[Path],
        region: str | None,
    ) -> None:
        uploads.update(
            {
                "config": config,
                "settings": settings,
                "reports": list(reports),
                "raw_files": list(raw_files),
                "region": region,
            }
        )

    monkeypatch.setattr(main, "upload_artifacts", capture_uploads)

    config = main.AuditConfig(fix_version="1.0.0", use_cache=True)

    issue_provider = DummyIssueProvider()
    commit_provider = DummyCommitProvider()

    result = main.run_audit(
        config,
        issue_provider=issue_provider,
        commit_provider=commit_provider,
    )

    assert issue_provider.calls and issue_provider.calls[0]["fix_version"] == "1.0.0"
    assert commit_provider.calls and commit_provider.calls[0]["use_cache"] is True
    assert result["summary"] == {"issues": 1, "commits": 1}
    assert uploads["region"] == "us-east-1"
    raw_paths = {Path(path) for path in uploads["raw_files"]}
    assert tmp_path / "commit-cache.json" in raw_paths
    assert tmp_path / "issue-cache.json" in raw_paths


def test_run_audit_uses_provider_factories(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    import importlib
    import sys

    fake_config = ModuleType("config")
    fake_settings = ModuleType("config.settings")
    fake_settings.load_settings = lambda overrides=None: {}
    fake_config.settings = fake_settings

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    monkeypatch.setitem(sys.modules, "config", fake_config)
    monkeypatch.setitem(sys.modules, "config.settings", fake_settings)
    importlib.invalidate_caches()
    main = importlib.import_module("main")

    data_dir = tmp_path / "data"
    temp_dir = tmp_path / "temp"
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "TEMP_DIR", temp_dir)

    settings = {
        "aws": {"region": "us-east-1"},
        "storage": {"s3": {}, "dynamodb": {"jira_issue_table": "table"}},
        "bitbucket": {
            "workspace": "workspace",
            "default_branches": ["main"],
            "repositories": ["repo"],
            "credentials": {},
        },
        "jira": {"base_url": "https://example", "credentials": {}},
    }

    monkeypatch.setattr(main, "load_settings", lambda overrides=None: settings)

    issue_factory_calls: list[dict[str, Any]] = []
    commit_factory_calls: list[dict[str, Any]] = []

    class DummyIssueProvider:
        def fetch_issues(
            self, *, fix_version: str, use_cache: bool = False
        ) -> tuple[list[dict[str, Any]], Path]:
            cache_path = tmp_path / "factory-issue.json"
            cache_path.write_text("{}", encoding="utf-8")
            return ([{"key": "ISSUE-2"}]), cache_path

    class DummyCommitProvider:
        def __init__(self) -> None:
            self._cache_path = tmp_path / "factory-commit.json"
            self._cache_path.write_text("{}", encoding="utf-8")

        def fetch_commits(
            self,
            *,
            repositories: Iterable[str],
            branches: Iterable[str],
            start: datetime,
            end: datetime,
            use_cache: bool = False,
        ) -> tuple[list[dict[str, Any]], list[str]]:
            return ([{"hash": "def456", "repository": "repo", "branch": "main"}]), [
                "factory-cache"
            ]

        def get_last_cache_file(self, name: str) -> Path | None:
            return self._cache_path if name == "factory-cache" else None

    def issue_factory(settings_arg: dict[str, Any]) -> DummyIssueProvider:
        issue_factory_calls.append(settings_arg)
        return DummyIssueProvider()

    def commit_factory(settings_arg: dict[str, Any]) -> DummyCommitProvider:
        commit_factory_calls.append(settings_arg)
        return DummyCommitProvider()

    monkeypatch.setattr(
        main,
        "build_jira_store",
        lambda settings: (_ for _ in ()).throw(
            AssertionError("should not build store")
        ),
    )
    monkeypatch.setattr(
        main,
        "build_bitbucket_client",
        lambda settings: (_ for _ in ()).throw(
            AssertionError("should not build client")
        ),
    )

    monkeypatch.setattr(
        main,
        "AuditProcessor",
        lambda *, issues, commits: SimpleNamespace(
            process=lambda: SimpleNamespace(
                summary={"issues": len(issues), "commits": len(commits)},
                stories_with_no_commits=[],
                orphan_commits=[],
                commit_story_mapping=[],
            )
        ),
    )

    class DummyExcelExporter:
        def __init__(self, output_dir: Path) -> None:
            self.output_dir = output_dir
            self.output_dir.mkdir(parents=True, exist_ok=True)

        def export(self, data: dict[str, Any], filename: str) -> Path:
            path = self.output_dir / filename
            path.write_text("excel", encoding="utf-8")
            return path

    monkeypatch.setattr(main, "ExcelExporter", DummyExcelExporter)

    monkeypatch.setattr(
        main,
        "upload_artifacts",
        lambda **_: None,
    )

    config = main.AuditConfig(fix_version="2.0.0")

    result = main.run_audit(
        config,
        issue_provider_factory=issue_factory,
        commit_provider_factory=commit_factory,
    )

    assert issue_factory_calls and issue_factory_calls[0] is settings
    assert commit_factory_calls and commit_factory_calls[0] is settings
    assert result["summary"] == {"issues": 1, "commits": 1}
