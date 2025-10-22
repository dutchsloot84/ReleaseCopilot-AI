"""Tests for the generator drift pre-commit hook."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from tools.hooks import check_generator_drift as drift


class _FakeResult:
    returncode = 0


def test_main_succeeds_without_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[tuple[str, ...], Path]] = []

    def fake_run(
        command: tuple[str, ...] | list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> _FakeResult:
        assert env is not None
        assert "PYTHONPATH" in env
        effective_cwd = Path(cwd) if cwd is not None else drift.REPO_ROOT
        calls.append((tuple(command), effective_cwd))
        return _FakeResult()

    monkeypatch.setattr(drift, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(drift, "_run", fake_run)
    monkeypatch.delenv("RELEASECOPILOT_SKIP_GENERATOR", raising=False)

    exit_code = drift.main([])

    assert exit_code == 0
    assert calls == [
        (
            (
                sys.executable,
                "-m",
                "releasecopilot.cli_releasecopilot",
                "generate",
                "--spec",
                drift.DEFAULT_SPEC.as_posix(),
                "--timezone",
                drift.DEFAULT_TIMEZONE,
                "--archive",
            ),
            tmp_path,
        ),
        (("git", "diff", "--stat", "--exit-code", *drift.GENERATED_PATHS), tmp_path),
    ]


def test_main_returns_nonzero_when_drift_detected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake_run(
        command: tuple[str, ...] | list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> _FakeResult:
        assert env is not None
        assert "PYTHONPATH" in env
        if tuple(command)[:3] == ("git", "diff", "--stat"):
            raise subprocess.CalledProcessError(returncode=1, cmd=list(command))
        return _FakeResult()

    monkeypatch.setattr(drift, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(drift, "_run", fake_run)
    monkeypatch.delenv("RELEASECOPILOT_SKIP_GENERATOR", raising=False)

    exit_code = drift.main([])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Generator drift detected" in captured.err
