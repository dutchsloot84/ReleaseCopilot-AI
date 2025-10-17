"""Tests for guarding against generator drift in CI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.github import wave2_helper as generator


def _run_generator(spec: dict[str, object]) -> None:
    """Render key generator artifacts with a deterministic timestamp."""

    Path("docs/mop").mkdir(parents=True, exist_ok=True)
    wave = int(spec["wave"])
    timestamp = generator.resolve_generated_at(wave)
    generator.render_mop_from_yaml(spec, generated_at=timestamp)
    items = generator.render_subprompts_and_issues(spec, generated_at=timestamp)
    generator.write_manifest(wave, items, generated_at=timestamp)


def _git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command inside the provided repository."""

    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
    )


def _run_guard(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Emulate the drift guard by checking for diffs in generator outputs."""

    return subprocess.run(
        [
            "git",
            "diff",
            "--stat",
            "--exit-code",
            "backlog",
            "docs/sub-prompts",
            "docs/mop",
            "artifacts/issues",
            "artifacts/manifests",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_drift_guard_detects_changes(
    generator_env: Path, sample_spec: dict[str, object]
) -> None:
    """The guard should fail when artifacts drift and pass once regenerated."""

    repo = generator_env
    _run_generator(sample_spec)

    _git("init", cwd=repo)
    _git("config", "user.email", "ci@example.com", cwd=repo)
    _git("config", "user.name", "CI", cwd=repo)
    _git("add", ".", cwd=repo)
    _git("commit", "-m", "baseline", cwd=repo)

    clean = _run_guard(repo)
    assert clean.returncode == 0, clean.stderr or clean.stdout

    wave = int(sample_spec["wave"])
    manifest_path = repo / "artifacts/manifests" / f"wave{wave}_subprompts.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["timezone"] = "UTC"
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    drift = _run_guard(repo)
    assert drift.returncode != 0

    _run_generator(sample_spec)
    restored = _run_guard(repo)
    assert restored.returncode == 0, restored.stderr or restored.stdout
