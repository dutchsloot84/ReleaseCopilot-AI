"""Tests for the generator drift pre-commit hook."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

import pytest

from tools.hooks import check_generator_drift as drift


class _FakeResult:
    returncode = 0


def test_ensure_requirements_installed_creates_marker_without_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_dir = tmp_path / "venv"
    env_dir.mkdir()
    calls: list[tuple[str, ...]] = []

    def fake_run(command: Sequence[str], *, check: bool, text: bool) -> _FakeResult:  # type: ignore[override]
        calls.append(tuple(command))
        assert check and text
        return _FakeResult()

    monkeypatch.setenv("PRE_COMMIT", "1")
    monkeypatch.setattr(sys, "prefix", env_dir.as_posix())
    monkeypatch.setattr(drift.subprocess, "run", fake_run)

    drift._ensure_requirements_installed()
    marker = env_dir / drift.HOOK_MARKER_FILENAME
    assert marker.exists()
    assert not calls

    calls.clear()
    drift._ensure_requirements_installed()
    assert not calls


def test_ensure_requirements_installed_skips_when_not_precommit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PRE_COMMIT", raising=False)
    monkeypatch.setattr(sys, "prefix", sys.prefix)
    calls: list[tuple[str, ...]] = []

    def fake_run(command: Sequence[str], *, check: bool, text: bool) -> _FakeResult:  # type: ignore[override]
        calls.append(tuple(command))
        return _FakeResult()

    monkeypatch.setattr(drift.subprocess, "run", fake_run)
    drift._ensure_requirements_installed()
    assert not calls


def test_build_env_injects_src_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTHONPATH", "/tmp/custom")
    env = drift._build_env({})
    src_path = (drift.REPO_ROOT / "src").as_posix()
    pythonpath_parts = env["PYTHONPATH"].split(os.pathsep)
    assert pythonpath_parts[0] == src_path
    assert pythonpath_parts[-1] == "/tmp/custom"


def test_main_succeeds_without_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[tuple[str, ...], Path]] = []

    def fake_run(
        command: tuple[str, ...] | list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> _FakeResult:
        del env
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
                "main.py",
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
        del env
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
