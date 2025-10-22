"""End-to-end tests for release export orchestration."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from zoneinfo import ZoneInfo

from config.loader import Defaults
from releasecopilot.orchestrator.release_exports import run_release_exports


@pytest.fixture()
def sample_defaults(tmp_path: Path) -> Defaults:
    repo_root = Path(__file__).resolve().parents[4]
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    return Defaults(
        project_root=tmp_path,
        cache_dir=tmp_path / "cache",
        artifact_dir=tmp_path / "dist",
        reports_dir=reports_dir,
        settings_path=repo_root / "config" / "defaults.yml",
        export_formats=("json", "excel"),
    )


def _write_report(directory: Path, name: str, payload: dict[str, object], *, mtime: float) -> None:
    path = directory / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_release_export_writes_artifacts(tmp_path: Path, sample_defaults: Defaults, monkeypatch: pytest.MonkeyPatch) -> None:
    reports_dir = sample_defaults.reports_dir
    artifact_root = tmp_path / "artifacts"

    report_payload = {
        "commit_story_mapping": [
            {
                "story_key": "APP-1",
                "story_summary": "Implement feature",
                "story_type": "Story",
            }
        ]
    }
    timestamp = time.time()
    _write_report(reports_dir, "report_old.json", report_payload, mtime=timestamp - 60)
    _write_report(reports_dir, "report_new.json", report_payload, mtime=timestamp)

    issues_payload = [
        {
            "key": "APP-1",
            "summary": "Implement feature",
            "issue_type": "Story",
            "uri": "https://example.invalid/browse/APP-1",
            "deployment_notes": {"markdown": "Ready for deployment"},
        }
    ]
    (reports_dir / "issues.json").write_text(json.dumps(issues_payload), encoding="utf-8")

    settings = {
        "jira": {"base_url": "https://example.invalid"},
        "release": {"validation_doc": {"deployment_notes_field_id": "deployment_notes"}},
    }
    monkeypatch.setattr("releasecopilot.orchestrator.release_exports.load_settings", lambda *args, **kwargs: settings)

    result = run_release_exports(
        reports_dir=reports_dir,
        artifact_root=artifact_root,
        defaults=sample_defaults,
        run_id="test-run",
        git_sha="abc123",
        now=datetime(2024, 5, 1, 12, 0, tzinfo=ZoneInfo("America/Phoenix")),
    )

    release_json = Path(result.release_notes["json"])
    assert release_json.exists()
    payload = json.loads(release_json.read_text(encoding="utf-8"))
    assert payload["run_id"] == "test-run"
    assert payload["timezone"] == "America/Phoenix"
    assert payload["notes"]["Story"][0]["issue_key"] == "APP-1"

    validation_json = Path(result.validation["json"])
    data = json.loads(validation_json.read_text(encoding="utf-8"))
    assert data["deployment_notes_field_id"] == "deployment_notes"
    assert data["items"][0]["deployment_notes"] == "Ready for deployment"

    release_excel = Path(result.release_notes["excel"])
    assert release_excel.exists()
    sheets = pd.read_excel(release_excel, sheet_name=None)
    assert "Metadata" in sheets
    assert "Story" in sheets
    assert sheets["Metadata"]["run_id"].iloc[0] == "test-run"

    assert (artifact_root / "release_notes" / "latest.json").exists()
    assert (artifact_root / "validation" / "latest.xlsx").exists()
