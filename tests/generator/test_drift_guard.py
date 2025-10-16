from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _clone_repo(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    destination = tmp_path / "repo"
    shutil.copytree(repo_root, destination, ignore=shutil.ignore_patterns(".git"))
    subprocess.run(
        ["git", "init"], cwd=destination, check=True, stdout=subprocess.DEVNULL
    )
    subprocess.run(
        ["git", "config", "user.email", "ci@example.com"], cwd=destination, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "CI Bot"], cwd=destination, check=True
    )
    subprocess.run(
        [
            "python",
            "main.py",
            "generate",
            "--spec",
            "backlog/wave3.yaml",
            "--timezone",
            "America/Phoenix",
        ],
        cwd=destination,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "add", "--all"], cwd=destination, check=True, stdout=subprocess.DEVNULL
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=destination,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return destination


def test_drift_guard_passes_on_clean_tree(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path)
    script = repo / "scripts" / "ci" / "check_generator_drift.sh"
    completed = subprocess.run([str(script)], cwd=repo)
    assert completed.returncode == 0


def test_drift_guard_detects_changes(tmp_path: Path) -> None:
    repo = _clone_repo(tmp_path)
    target = repo / "docs" / "mop" / "mop_wave3.md"
    target.write_text(
        target.read_text(encoding="utf-8") + "\nExtra drift", encoding="utf-8"
    )
    subprocess.run(
        ["git", "commit", "-am", "introduce drift"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    script = repo / "scripts" / "ci" / "check_generator_drift.sh"
    completed = subprocess.run([str(script)], cwd=repo)
    assert completed.returncode != 0
