from __future__ import annotations

import importlib
import types
from datetime import datetime
from pathlib import Path

import pytest


@pytest.fixture
def main_module() -> types.ModuleType:
    import main

    return importlib.reload(main)


@pytest.fixture
def fixed_datetime(monkeypatch: pytest.MonkeyPatch, main_module: types.ModuleType) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def utcnow(cls) -> "FixedDatetime":  # type: ignore[override]
            return cls(2025, 10, 24, 15, 30, 0)

    monkeypatch.setattr(main_module, "datetime", FixedDatetime)


def test_upload_artifacts_builds_versioned_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    main_module: types.ModuleType,
    fixed_datetime,
) -> None:
    reports = []
    raw_files = []
    for name in ("report.json", "report.xlsx", "summary.json"):
        path = tmp_path / name
        path.write_text("data", encoding="utf-8")
        reports.append(path)
    for name in ("jira.json", "commits.json", "cache.json"):
        path = tmp_path / name
        path.write_text("data", encoding="utf-8")
        raw_files.append(path)

    temp_dir = tmp_path / "temp"
    monkeypatch.setattr(main_module, "TEMP_DIR", temp_dir)
    monkeypatch.setattr(main_module, "_detect_git_sha", lambda: "abcdef123456")

    calls: list[dict] = []

    def fake_build_client(*, region_name=None):
        return "client"

    def fake_upload_directory(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(main_module.uploader, "build_s3_client", fake_build_client)
    monkeypatch.setattr(main_module.uploader, "upload_directory", fake_upload_directory)

    config = main_module.AuditConfig(
        fix_version="2025.10.24", s3_bucket="bucket", s3_prefix="audits"
    )
    settings = {"aws": {}}

    main_module.upload_artifacts(
        config=config,
        settings=settings,
        reports=reports,
        raw_files=raw_files,
        region="us-east-1",
    )

    assert len(calls) == 3

    expected_scope = "2025.10.24/2025-10-24_153000"
    prefixes = {call["prefix"] for call in calls}
    assert prefixes == {
        "audits/artifacts/json",
        "audits/artifacts/excel",
        "audits/temp_data",
    }
    assert {call["subdir"] for call in calls} == {expected_scope}
    for call in calls:
        assert call["bucket"] == "bucket"
        assert call["client"] == "client"
        metadata = call["metadata"]
        assert metadata["fix-version"] == "2025.10.24"
        assert metadata["generated-at"] == "2025-10-24T15:30:00Z"
        assert metadata["git-sha"] == "abcdef123456"


def test_upload_artifacts_skips_when_bucket_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    main_module: types.ModuleType,
) -> None:
    monkeypatch.setattr(main_module, "TEMP_DIR", tmp_path / "temp")

    calls: list[dict] = []
    monkeypatch.setattr(
        main_module.uploader, "upload_directory", lambda **kwargs: calls.append(kwargs)
    )

    config = main_module.AuditConfig(fix_version="2025.10.24")
    settings = {"aws": {}}

    main_module.upload_artifacts(
        config=config,
        settings=settings,
        reports=[],
        raw_files=[],
        region=None,
    )

    assert calls == []
