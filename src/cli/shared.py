"""Shared CLI helpers for ReleaseCopilot entry points."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Optional, TextIO, Tuple


@dataclass
class AuditConfig:
    """Configuration payload produced by the CLI argument parser."""

    fix_version: str
    repos: list[str] = field(default_factory=list)
    branches: Optional[list[str]] = None
    window_days: int = 28
    freeze_date: Optional[str] = None
    develop_only: bool = False
    use_cache: bool = False
    s3_bucket: Optional[str] = None
    s3_prefix: Optional[str] = None
    output_prefix: str = "audit_results"


def build_parser() -> argparse.ArgumentParser:
    """Return the canonical argument parser for ReleaseCopilot CLI entry points."""

    parser = argparse.ArgumentParser(description="ReleaseCopilot audit runner")
    parser.add_argument("--fix-version", required=True, help="Jira fix version to audit")
    parser.add_argument(
        "--repos", nargs="*", default=[], help="Bitbucket repositories to inspect"
    )
    parser.add_argument("--branches", nargs="*", help="Optional branches to include")
    parser.add_argument(
        "--develop-only", action="store_true", help="Use the develop branch only"
    )
    parser.add_argument("--freeze-date", help="ISO freeze date override")
    parser.add_argument(
        "--window-days", type=int, default=28, help="Lookback window in days"
    )
    parser.add_argument(
        "--use-cache", action="store_true", help="Reuse cached payloads"
    )
    parser.add_argument("--s3-bucket", help="Override destination S3 bucket")
    parser.add_argument("--s3-prefix", help="Override destination S3 prefix")
    parser.add_argument(
        "--output-prefix", default="audit_results", help="Basename for generated files"
    )
    parser.add_argument(
        "--output", help="Optional directory to copy generated artifacts into"
    )
    parser.add_argument(
        "--format",
        choices=["json", "excel", "both"],
        default="both",
        help="Artifact copy format",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip remote calls and only echo configuration",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging verbosity")
    return parser


def parse_args(
    argv: Optional[Iterable[str]] = None,
) -> Tuple[argparse.Namespace, AuditConfig]:
    """Parse CLI arguments and construct the :class:`AuditConfig` payload."""

    parser = build_parser()
    args = parser.parse_args(argv)
    config = AuditConfig(
        fix_version=args.fix_version,
        repos=list(args.repos),
        branches=list(args.branches) if args.branches else None,
        window_days=args.window_days,
        freeze_date=args.freeze_date,
        develop_only=args.develop_only,
        use_cache=args.use_cache,
        s3_bucket=args.s3_bucket or os.getenv("ARTIFACTS_BUCKET"),
        s3_prefix=args.s3_prefix,
        output_prefix=args.output_prefix,
    )
    return args, config


def _select_artifacts(
    artifacts: Mapping[str, str], format_preference: str
) -> dict[str, str]:
    """Filter artifacts according to the requested ``--format`` value."""

    if format_preference == "both":
        return {name: path for name, path in artifacts.items() if path}

    allowed_suffixes: MutableMapping[str, set[str]] = {
        "json": {".json"},
        "excel": {".xlsx"},
    }
    suffixes = allowed_suffixes.get(format_preference, {".json", ".xlsx"})
    selected: dict[str, str] = {}
    for name, path in artifacts.items():
        if not path:
            continue
        suffix = Path(path).suffix.lower()
        if suffix in suffixes:
            selected[name] = path
    return selected


def copy_artifacts(artifacts: Mapping[str, str], destination: Path) -> None:
    """Copy artifact files into ``destination`` preserving filenames."""

    destination.mkdir(parents=True, exist_ok=True)
    for path in artifacts.values():
        if not path:
            continue
        source = Path(path)
        if not source.exists() or not source.is_file():
            continue
        shutil.copy2(source, destination / source.name)


def handle_dry_run(config: AuditConfig, *, stdout: Optional[TextIO] = None) -> None:
    """Emit the configuration payload for ``--dry-run`` executions."""

    stream = stdout or sys.stdout
    print(json.dumps({"config": asdict(config)}, indent=2), file=stream)


def finalize_run(
    result: Mapping[str, object],
    args: argparse.Namespace,
    *,
    stdout: Optional[TextIO] = None,
) -> None:
    """Print the summary and optionally stage artifacts for local inspection."""

    stream = stdout or sys.stdout
    summary = result.get("summary", {}) if isinstance(result, Mapping) else {}
    print(json.dumps(summary, indent=2), file=stream)

    output_dir = Path(args.output) if getattr(args, "output", None) else None
    if not output_dir:
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = (
        result.get("artifacts", {})
        if isinstance(result, Mapping)
        else {}  # pragma: no cover - defensive guard
    )
    if isinstance(artifacts, Mapping) and artifacts:
        selected = _select_artifacts(artifacts, getattr(args, "format", "both"))
        if selected:
            copy_artifacts(selected, output_dir)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

