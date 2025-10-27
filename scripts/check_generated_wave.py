#!/usr/bin/env python
"""Check that committed Wave artifacts match regenerated outputs."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

wave_generator = importlib.import_module("tools.generator.generator")
DEFAULT_SPEC = ROOT / "backlog" / "wave3.yaml"
DEFAULT_TIMEZONE = "America/Phoenix"
TARGET_PATHS: tuple[Path, ...] = (
    Path("docs/mop"),
    Path("docs/sub-prompts"),
    Path("artifacts/issues"),
    Path("artifacts/manifests"),
)


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="check", choices=["check"], help="Validation mode")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC), help="Wave specification file")
    parser.add_argument(
        "--timezone",
        default=DEFAULT_TIMEZONE,
        help="Timezone passed to the generator (default: America/Phoenix)",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _resolve_spec_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _load_wave_number(spec_path: Path) -> int:
    spec = wave_generator.load_spec(spec_path)
    wave_value = spec.get("wave")
    if wave_value is None:
        raise ValueError(f"Spec {spec_path} is missing required 'wave' field")
    return int(wave_value)


def _load_manifest_metadata(wave: int) -> tuple[datetime | None, str | None]:
    manifest = ROOT / "artifacts" / "manifests" / f"wave{wave}_subprompts.json"
    if not manifest.exists():
        return None, None
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, None
    generated_at_raw = payload.get("generated_at")
    git_sha_raw = payload.get("git_sha")
    generated_at: datetime | None = None
    if isinstance(generated_at_raw, str) and generated_at_raw.strip():
        try:
            generated_at = datetime.fromisoformat(generated_at_raw.strip())
        except ValueError:
            generated_at = None
    git_sha: str | None = None
    if isinstance(git_sha_raw, str) and git_sha_raw.strip():
        git_sha = git_sha_raw.strip()
    return generated_at, git_sha


def _copy_support_files(destination: Path) -> None:
    templates_src = ROOT / "templates"
    if templates_src.exists():
        shutil.copytree(templates_src, destination / "templates")


@contextmanager
def _temporary_env(name: str, value: str | None):
    original = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = original


def _generate_artifacts(
    *,
    destination: Path,
    spec_path: Path,
    timezone: str,
    existing_timestamp: datetime | None,
    git_sha: str | None,
) -> None:
    kwargs: dict[str, object] = {
        "spec_path": spec_path,
        "base_dir": destination,
        "timezone": timezone,
        "archive_previous": False,
    }
    if existing_timestamp is not None:
        kwargs["now"] = lambda: existing_timestamp
    with _temporary_env("GIT_SHA", git_sha):
        wave_generator.generate_from_yaml(**kwargs)


def _collect_files(root: Path, paths: Iterable[Path]) -> tuple[dict[Path, Path], list[Path]]:
    files: dict[Path, Path] = {}
    missing: list[Path] = []
    for rel in paths:
        target = root / rel
        if not target.exists():
            missing.append(rel)
            continue
        if target.is_dir():
            for item in sorted(target.rglob("*")):
                if item.is_file():
                    files[item.relative_to(root)] = item
        elif target.is_file():
            files[target.relative_to(root)] = target
        else:
            missing.append(rel)
    return files, missing


def _compare(committed: Mapping[Path, Path], produced: Mapping[Path, Path]) -> list[str]:
    issues: list[str] = []
    for rel, committed_path in committed.items():
        generated_path = produced.get(rel)
        if generated_path is None:
            issues.append(f"generator did not produce {rel.as_posix()}")
            continue
        if committed_path.read_bytes() != generated_path.read_bytes():
            issues.append(f"stale artifact detected at {rel.as_posix()}")
    for rel in produced:
        if rel not in committed:
            issues.append(f"unexpected artifact produced: {rel.as_posix()}")
    return issues


def _report_and_exit(issues: list[str]) -> int:
    if not issues:
        return 0
    print("Wave artifacts are stale or missing:", file=sys.stderr)
    for entry in issues:
        print(f"- {entry}", file=sys.stderr)
    print(
        "\nFix locally:\n  make gen-wave\nthen commit the refreshed artifacts.",
        file=sys.stderr,
    )
    return 1


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    spec_path = _resolve_spec_path(args.spec)
    wave = _load_wave_number(spec_path)
    existing_timestamp, git_sha = _load_manifest_metadata(wave)

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = Path(tmp_dir)
        _copy_support_files(temp_root)
        _generate_artifacts(
            destination=temp_root,
            spec_path=spec_path,
            timezone=args.timezone,
            existing_timestamp=existing_timestamp,
            git_sha=git_sha,
        )
        committed_files, committed_missing = _collect_files(ROOT, TARGET_PATHS)
        generated_files, generated_missing = _collect_files(temp_root, TARGET_PATHS)

        issues = []
        issues.extend(f"missing committed path: {path.as_posix()}" for path in committed_missing)
        issues.extend(f"generator did not create {path.as_posix()}" for path in generated_missing)
        issues.extend(_compare(committed_files, generated_files))
    return _report_and_exit(issues)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
