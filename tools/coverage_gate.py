"""Fail fast when coverage falls below the required project threshold."""

from __future__ import annotations

import argparse
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from releasecopilot.utils.coverage import enforce_threshold


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report",
        type=Path,
        help="Path to a coverage JSON or XML report (e.g. coverage.json)",
    )
    parser.add_argument(
        "--minimum",
        type=float,
        default=70.0,
        help="Minimum acceptable coverage percentage (default: 70.0)",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Optional list of paths to enforce (defaults to overall totals)",
    )
    return parser


def main(argv: list[str] | None = None) -> float:
    parser = _build_parser()
    args = parser.parse_args(argv)
    totals = enforce_threshold(args.report, args.minimum, include=args.paths)
    scope = f" paths={len(args.paths)}" if args.paths else ""
    print(f"coverage={totals.percent:.2f}% threshold={args.minimum:.2f}%{scope}")
    return totals.percent


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
