from __future__ import annotations

from pathlib import Path


def test_hook_requirements_file_lists_dependencies() -> None:
    requirements = Path("tools/hooks/requirements.txt").read_text(encoding="utf-8")
    assert "# Generator hook dependencies" in requirements
    assert "requests" not in requirements
