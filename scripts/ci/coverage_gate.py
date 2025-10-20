#!/usr/bin/env python3
"""Enforce the repository coverage threshold and surface uncovered lines."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import List, Tuple
import xml.etree.ElementTree as ET

THRESHOLD = float(os.environ.get("COVERAGE_THRESHOLD", "70"))


def _load_report(path: Path) -> ET.Element:
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"Failed to parse coverage report {path}: {exc}") from exc


def _collect_uncovered(root: ET.Element) -> List[Tuple[str, float, List[int]]]:
    uncovered: List[Tuple[str, float, List[int]]] = []
    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename")
        if not filename:
            continue
        line_rate = float(cls.attrib.get("line-rate", "0")) * 100
        missing: List[int] = []
        for line in cls.findall("lines/line"):
            hits = int(line.attrib.get("hits", "0"))
            if hits == 0:
                missing.append(int(line.attrib.get("number", "0")))
        if missing:
            uncovered.append((filename, line_rate, sorted(missing)))
    uncovered.sort(key=lambda item: (item[1], -len(item[2])))
    return uncovered


def main(argv: List[str]) -> int:
    report_path = Path(argv[1]) if len(argv) > 1 else Path("coverage.xml")
    if not report_path.exists():
        print(f"Coverage report not found: {report_path}", file=sys.stderr)
        return 1

    root = _load_report(report_path)
    total_rate = float(root.attrib.get("line-rate", "0")) * 100
    print(f"Overall coverage: {total_rate:.2f}% (required: {THRESHOLD:.2f}%)")

    uncovered = _collect_uncovered(root)[:5]
    if uncovered:
        print("Most uncovered files:")
        for filename, rate, missing in uncovered:
            preview = ", ".join(str(num) for num in missing[:5])
            print(f"  - {filename} — {rate:.2f}% covered; first uncovered lines: {preview}")
    else:
        print("All tracked lines executed at least once in tests.")

    if total_rate < THRESHOLD:
        print(
            f"Coverage check failed: {total_rate:.2f}% < {THRESHOLD:.2f}% threshold",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
