"""Smoke tests ensuring the new console entry points remain pure."""

from __future__ import annotations

import importlib
import sys

import pytest


def test_main_wrapper_import_keeps_sys_path_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    original = list(sys.path)
    module = importlib.reload(importlib.import_module("main"))
    assert module.main is not None
    assert sys.path == original


def test_wave2_entrypoint_converts_system_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_main(*, args: list[str] | None, standalone_mode: bool) -> None:
        captured["args"] = args
        captured["standalone_mode"] = standalone_mode
        raise SystemExit(5)

    monkeypatch.setattr("releasecopilot.entrypoints.wave2.wave2_cli.main", fake_main, raising=True)

    from releasecopilot.entrypoints import wave2

    code = wave2.main(["--dry-run"])
    assert code == 5
    assert captured["args"] == ["--dry-run"]
    assert captured["standalone_mode"] is False
