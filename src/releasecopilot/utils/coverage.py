"""Utilities for parsing coverage reports and enforcing minimum thresholds."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


class CoverageReportError(RuntimeError):
    """Raised when a coverage report cannot be parsed."""


@dataclass(frozen=True)
class CoverageTotals:
    """Aggregate coverage statistics extracted from a report."""

    covered: float
    total: float
    percent: float


_IGNORED_ROOTS = frozenset({"tests", "tools"})


def _normalize(path: str) -> str:
    return Path(path).as_posix().lstrip("./")


def _root_for(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else path


def _totals_from_counts(covered: float, total: float) -> CoverageTotals:
    percent = 100.0 if total == 0 else (covered / total) * 100.0
    return CoverageTotals(covered=covered, total=total, percent=percent)


def _coerce_float(value: Any, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise CoverageReportError("coverage JSON value is not numeric") from exc


def _parse_json_totals(data: Any) -> CoverageTotals:
    if not isinstance(data, dict):
        raise CoverageReportError("coverage JSON payload must be a dictionary")

    totals = data.get("totals")
    if not isinstance(totals, dict):
        raise CoverageReportError("coverage JSON missing 'totals'")

    covered = _coerce_float(totals.get("covered_lines", totals.get("covered_statements", 0)))
    total = _coerce_float(totals.get("num_statements", totals.get("statements", 0)))

    raw_percent: Any = totals.get("percent_covered")
    if raw_percent is None:
        raw_percent = totals.get("percent_covered_display")

    if raw_percent is None:
        percent = _totals_from_counts(covered, total).percent
    else:
        try:
            percent = float(raw_percent)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise CoverageReportError("coverage JSON percent is not numeric") from exc

    return CoverageTotals(covered=covered, total=total, percent=percent)


def _parse_json_subset(data: Any, include: Iterable[str]) -> CoverageTotals:
    if not isinstance(data, dict):
        raise CoverageReportError("coverage JSON payload must be a dictionary")

    files = data.get("files")
    if not isinstance(files, dict):
        raise CoverageReportError("coverage JSON missing 'files' map")

    include_set = {_normalize(path) for path in include if path.endswith(".py")}
    if not include_set:
        return _parse_json_totals(data)

    coverage_by_path: dict[str, dict[str, Any]] = {
        _normalize(path): details for path, details in files.items() if isinstance(details, dict)
    }
    covered_roots = {_root_for(path) for path in coverage_by_path}
    covered = 0.0
    total = 0.0
    missing: list[str] = []

    for path in sorted(include_set):
        summary = coverage_by_path.get(path)
        if summary is None:
            root = _root_for(path)
            if root not in _IGNORED_ROOTS and root in covered_roots:
                missing.append(path)
            continue

        summary_map = summary.get("summary")
        if not isinstance(summary_map, dict):
            raise CoverageReportError(f"coverage JSON missing summary for {path}")

        covered += _coerce_float(summary_map.get("covered_lines", 0))
        total += _coerce_float(summary_map.get("num_statements", 0))

    if missing:
        raise SystemExit("Coverage data missing for: " + ", ".join(sorted(missing)))

    return _totals_from_counts(covered, total)


def _parse_xml_totals(text: str) -> CoverageTotals:
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:  # pragma: no cover - defensive
        raise CoverageReportError("coverage XML is not valid") from exc

    line_rate = root.attrib.get("line-rate")
    covered_attr = root.attrib.get("lines-covered")
    valid_attr = root.attrib.get("lines-valid")

    if line_rate is None or covered_attr is None or valid_attr is None:
        raise CoverageReportError("coverage XML missing summary attributes")

    try:
        covered = float(covered_attr)
        total = float(valid_attr)
    except ValueError as exc:  # pragma: no cover - defensive
        raise CoverageReportError("coverage XML counts are not numeric") from exc

    try:
        percent = float(line_rate) * 100.0
    except ValueError as exc:  # pragma: no cover - defensive
        raise CoverageReportError("coverage XML line-rate is not numeric") from exc

    return CoverageTotals(covered=covered, total=total, percent=percent)


def load_totals(report: Path, include: Iterable[str] | None = None) -> CoverageTotals:
    """Return :class:`CoverageTotals` for the provided coverage ``report``.

    Supports ``coverage json`` reports and the standard ``coverage xml`` schema.
    When ``include`` is provided the JSON payload must contain the per-file
    details produced by ``coverage json`` and the aggregation is restricted to
    the matching paths.
    """

    if not report.exists():
        raise CoverageReportError(f"coverage report {report} does not exist")

    suffix = report.suffix.lower()
    text = report.read_text(encoding="utf-8")

    if suffix == ".json":
        payload = json.loads(text)
        if include is not None:
            return _parse_json_subset(payload, include)
        return _parse_json_totals(payload)

    if suffix == ".xml":
        if include is not None:
            raise CoverageReportError("path filtering requires a JSON coverage report")
        return _parse_xml_totals(text)

    raise CoverageReportError("unsupported coverage report format; expected JSON or XML")


def enforce_threshold(
    report: Path, minimum: float = 70.0, include: Iterable[str] | None = None
) -> CoverageTotals:
    """Validate that the ``report`` meets the ``minimum`` percentage.

    Returns the parsed :class:`CoverageTotals` for callers that need to reuse the
    aggregate coverage value. Raises :class:`SystemExit` when coverage falls
    below the required ``minimum``.
    """

    totals = load_totals(report, include=include)
    if totals.percent < minimum:
        raise SystemExit(f"Coverage {totals.percent:.1f}% is below required {minimum:.1f}%")
    return totals


__all__ = ["CoverageReportError", "CoverageTotals", "enforce_threshold", "load_totals"]
