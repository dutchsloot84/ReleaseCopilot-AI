"""Smoke tests for the module-based CLI entry points."""

from __future__ import annotations

import importlib
from pathlib import Path


def test_releasecopilot_cli_resolves_project_paths() -> None:
    module = importlib.import_module("releasecopilot.cli_releasecopilot")
    module = importlib.reload(module)
    repo_root = Path(__file__).resolve().parents[2]

    assert module.PROJECT_ROOT == repo_root
    assert module.DATA_DIR == repo_root / "data"
    assert module.TEMP_DIR == repo_root / "temp_data"
