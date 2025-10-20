from __future__ import annotations

from datetime import datetime
import json
from zoneinfo import ZoneInfo

from tracking.correlation import build_correlation_document, write_correlation_artifact


def test_build_correlation_document_and_write(tmp_path) -> None:
    issues = [{"key": "APP-1", "fields": {"summary": "Ready"}}]
    commits = [
        {
            "hash": "c1",
            "message": "APP-1 initial work",
            "branch": "feature/app-1",
        }
    ]

    document = build_correlation_document(
        issues=issues,
        commits=commits,
        args={"window_hours": 24},
        run_id="run-abc",
        git_sha="deadbeef",
        generated_at=datetime(2025, 1, 1, 12, tzinfo=ZoneInfo("UTC")),
        tz=ZoneInfo("America/Phoenix"),
    )

    assert document["run_id"] == "run-abc"
    assert document["git_sha"] == "deadbeef"
    assert document["timezone"] == "America/Phoenix"
    assert document["stories_without_commits"]["payload"] == []
    assert document["commits_without_story"]["payload"] == []
    assert document["matched"][0]["commit"]["hash"] == "c1"
    assert document["summary"]["matched_commits"] == len(document["matched"])

    destination = write_correlation_artifact(document, artifact_dir=tmp_path)
    assert destination.exists()

    latest = json.loads((tmp_path / "latest.json").read_text())
    assert latest["run_id"] == "run-abc"

    summary = json.loads((tmp_path / "latest_summary.json").read_text())
    assert summary["run_id"] == "run-abc"
    assert summary["summary"]["total_commits"] == 1
