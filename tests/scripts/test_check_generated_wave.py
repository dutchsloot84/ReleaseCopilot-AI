"""Tests for the hermetic Wave artifact checker."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import check_generated_wave as checker


@pytest.fixture(autouse=True)
def _restore_module_state():
    original_root = checker.ROOT
    original_targets = checker.TARGET_PATHS
    original_spec = checker.DEFAULT_SPEC
    original_generate = checker._generate_artifacts
    original_copy = checker._copy_support_files
    yield
    checker.ROOT = original_root
    checker.TARGET_PATHS = original_targets
    checker.DEFAULT_SPEC = original_spec
    checker._generate_artifacts = original_generate
    checker._copy_support_files = original_copy


def _setup_repo(tmp_path: Path) -> None:
    (tmp_path / "backlog").mkdir()
    (tmp_path / "backlog" / "wave3.yaml").write_text("wave: 3\n", encoding="utf-8")
    manifest_dir = tmp_path / "artifacts" / "manifests"
    manifest_dir.mkdir(parents=True)
    manifest_dir.joinpath("wave3_subprompts.json").write_text(
        "{" '\n  "generated_at": "2024-01-02T03:04:05-07:00",\n  "git_sha": "abc123"\n}\n',
        encoding="utf-8",
    )


def _monkeypatch_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    checker.ROOT = tmp_path
    checker.DEFAULT_SPEC = tmp_path / "backlog" / "wave3.yaml"
    checker.TARGET_PATHS = (Path("docs/mop/mop_wave3.md"),)

    def fake_generate(
        *,
        destination: Path,
        spec_path: Path,
        timezone: str,
        existing_timestamp,
        git_sha: str | None,
    ) -> None:
        del spec_path, timezone, existing_timestamp, git_sha
        destination.joinpath("docs", "mop").mkdir(parents=True, exist_ok=True)
        destination.joinpath("docs", "mop", "mop_wave3.md").write_text("content", encoding="utf-8")

    def fake_copy(destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(checker, "_generate_artifacts", fake_generate)
    monkeypatch.setattr(checker, "_copy_support_files", fake_copy)


def test_main_succeeds_when_artifacts_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _setup_repo(tmp_path)
    (tmp_path / "docs" / "mop").mkdir(parents=True)
    (tmp_path / "docs" / "mop" / "mop_wave3.md").write_text("content", encoding="utf-8")
    _monkeypatch_module(monkeypatch, tmp_path)

    exit_code = checker.main(["--mode", "check"])

    assert exit_code == 0


def test_main_reports_drift_when_bytes_differ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _setup_repo(tmp_path)
    (tmp_path / "docs" / "mop").mkdir(parents=True)
    (tmp_path / "docs" / "mop" / "mop_wave3.md").write_text("old", encoding="utf-8")
    _monkeypatch_module(monkeypatch, tmp_path)

    exit_code = checker.main(["--mode", "check"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "stale artifact" in captured.err
    assert "make gen-wave" in captured.err
