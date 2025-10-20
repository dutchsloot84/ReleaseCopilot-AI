from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from releasecopilot.ingest.bitbucket_scanner import BitbucketScanner
from releasecopilot.ingest.storage import CommitStorage


class StubBitbucketClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def iter_commits(self, **kwargs):
        self.calls.append(kwargs)
        for item in self._responses:
            yield dict(item)


def test_scan_commits_with_pagination(tmp_path: Path) -> None:
    tz = ZoneInfo("America/Phoenix")
    now = datetime(2024, 1, 2, 12, 0, tzinfo=tz)
    window_start = now - timedelta(hours=6)

    client = StubBitbucketClient(
        [
            {
                "hash": "abc123",
                "repository": "example/repo",
                "author": {"raw": "Alice"},
                "files": [{"path": "src/app.py"}, {"path": "src/app.py"}],
                "date": "2024-01-02T11:59:00-07:00",
            },
            {
                "hash": "def456",
                "repository": "example/repo",
                "author": {"user": {"display_name": "Bob"}},
                "files": [{"path": "README.md"}],
                "modified_on": "2024-01-02T11:30:00-07:00",
            },
        ]
    )

    storage = CommitStorage(tmp_path / "commits.db", tz=tz)
    scanner = BitbucketScanner(
        client=client,
        storage=storage,
        artifact_dir=tmp_path / "artifacts",
        tz=tz,
        git_sha_resolver=lambda: "feedbeef",
    )

    result = scanner.scan(repos=["example/repo"], hours=6, now=now)

    assert client.calls[0]["since"] == window_start
    assert len(result["commits"]) == 2
    assert storage.fetch_hashes() == {"abc123", "def456"}

    artifact_path = Path(result["artifact_path"])
    assert artifact_path.exists()
    artifact = json.loads(artifact_path.read_text())
    assert artifact["timezone"] == "America/Phoenix"
    assert artifact["window"]["repositories"] == ["example/repo"]
    assert artifact["window"]["start"].startswith("2024-01-02")
    assert artifact["payload"][0]["files_changed"] == ["src/app.py"]
    assert artifact["git_sha"] == "feedbeef"
