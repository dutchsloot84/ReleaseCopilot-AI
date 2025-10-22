"""Smoke tests around the bootstrap module's sys.path handling."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def test_bootstrap_places_src_first(monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = Path(__file__).resolve().parents[2]
    expected = str(project_root / "src")
    original_path = ["alpha", str(project_root), expected, "beta", expected]
    if monkeypatch is not None:
        monkeypatch.setattr(sys, "path", original_path.copy())
    else:
        sys.path = original_path.copy()

    module = importlib.import_module("releasecopilot_bootstrap")
    importlib.reload(module)

    assert sys.path[0] == expected
    assert sys.path.count(expected) == 1

    importlib.reload(module)

    assert sys.path[0] == expected
    assert sys.path.count(expected) == 1
