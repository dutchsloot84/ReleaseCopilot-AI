"""Tests for coverage parsing and enforcement helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from releasecopilot.utils import coverage


def test_load_totals_from_json(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "totals": {
                    "percent_covered": 82.5,
                    "covered_lines": 66,
                    "num_statements": 80,
                }
            }
        ),
        encoding="utf-8",
    )

    totals = coverage.load_totals(report)

    assert totals.percent == pytest.approx(82.5)
    assert totals.covered == pytest.approx(66)
    assert totals.total == pytest.approx(80)


def test_load_totals_from_xml(tmp_path: Path) -> None:
    report = tmp_path / "coverage.xml"
    report.write_text(
        '<coverage line-rate="0.750" lines-covered="150" lines-valid="200"></coverage>',
        encoding="utf-8",
    )

    totals = coverage.load_totals(report)

    assert totals.percent == pytest.approx(75.0)
    assert totals.covered == pytest.approx(150)
    assert totals.total == pytest.approx(200)


def test_load_totals_subset(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    payload = {
        "totals": {"covered_lines": 20, "num_statements": 40, "percent_covered": 50.0},
        "files": {
            "src/module_a.py": {"summary": {"covered_lines": 18, "num_statements": 20}},
            "src/module_b.py": {"summary": {"covered_lines": 2, "num_statements": 20}},
        },
    }
    report.write_text(json.dumps(payload), encoding="utf-8")

    totals = coverage.load_totals(report, include=["src/module_a.py"])

    assert totals.percent == pytest.approx(90.0)
    assert totals.covered == pytest.approx(18)
    assert totals.total == pytest.approx(20)


def test_enforce_threshold_raises_when_below(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"totals": {"percent_covered": 63.0}}), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        coverage.enforce_threshold(report, minimum=70.0)

    assert "below required" in str(exc.value)


def test_load_totals_rejects_missing_file(tmp_path: Path) -> None:
    report = tmp_path / "missing.json"

    with pytest.raises(coverage.CoverageReportError):
        coverage.load_totals(report)


def test_load_totals_subset_ignores_paths_outside_tracked_roots(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    payload = {
        "totals": {
            "percent_covered": 100.0,
            "covered_lines": 10,
            "num_statements": 10,
        },
        "files": {"src/module_a.py": {"summary": {"covered_lines": 10, "num_statements": 10}}},
    }
    report.write_text(json.dumps(payload), encoding="utf-8")

    totals = coverage.load_totals(
        report,
        include=[
            "src/module_a.py",
            "tests/test_module_a.py",
            "tools/helper.py",
        ],
    )

    assert totals.percent == pytest.approx(100.0)
    assert totals.covered == pytest.approx(10)
    assert totals.total == pytest.approx(10)


def test_load_totals_subset_reports_missing_for_tracked_roots(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    payload = {
        "totals": {
            "percent_covered": 0.0,
            "covered_lines": 0,
            "num_statements": 0,
        },
        "files": {},
    }
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        coverage.load_totals(report, include=["src/missing.py"])

    assert "src/missing.py" in str(exc.value)
