from __future__ import annotations

from pathlib import Path


def test_hook_requirements_file_lists_dependencies() -> None:
    requirements = Path("tools/hooks/requirements.txt").read_text(encoding="utf-8")
    assert "requests>=2.32" in requirements
    assert "python-slugify==8.0.0" in requirements
    assert "boto3" not in requirements
