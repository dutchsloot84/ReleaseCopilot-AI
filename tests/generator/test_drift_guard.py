from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("COVERAGE_PROCESS_START", None)
    env.pop("COVERAGE_FILE", None)
    env.setdefault("RELEASECOPILOT_SKIP_GENERATOR", "1")
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        stdout=subprocess.DEVNULL,
        env=env,
    )


def _clone_repo(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    destination = tmp_path / "repo"
    shutil.copytree(repo_root, destination, ignore=shutil.ignore_patterns(".git"))
    _run(["git", "init"], destination)
    _run(["git", "config", "user.email", "ci@example.com"], destination)
    _run(["git", "config", "user.name", "CI Bot"], destination)
    _run(["git", "add", "--all"], destination)
    _run(["git", "commit", "-m", "initial"], destination)
    return destination


def test_drift_guard_passes_on_clean_tree(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path)
    script = repo / "scripts" / "ci" / "check_generator_drift.sh"
    completed = _run([str(script)], repo, check=False)
    assert completed.returncode == 0


def test_drift_guard_detects_changes(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path)
    target = repo / "docs" / "mop" / "mop_wave3.md"
    target.write_text(
        target.read_text(encoding="utf-8") + "\nExtra drift", encoding="utf-8"
    )
    script = repo / "scripts" / "ci" / "check_generator_drift.sh"
    completed = _run([str(script)], repo, check=False)
    assert completed.returncode != 0
