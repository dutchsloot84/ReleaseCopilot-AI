from __future__ import annotations

import json
from pathlib import Path

import pytest

from exporters.excel_exporter import ExcelExporter
from tests.helpers.schema_validation import assert_excel_columns, assert_json_schema

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "schemas"
GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture(scope="module")
def audit_payload(tmp_path_factory: pytest.TempPathFactory) -> Path:
    payload_path = tmp_path_factory.mktemp("audit") / "audit_results.json"
    payload_path.write_text(
        (GOLDEN_DIR / "audit_results.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return payload_path


def test_json_export_matches_schema(audit_payload: Path) -> None:
    schema_path = SCHEMA_DIR / "audit_results.schema.json"
    assert_json_schema(audit_payload, schema_path)


def test_excel_export_columns(tmp_path: Path) -> None:
    payload = json.loads((GOLDEN_DIR / "audit_results.json").read_text(encoding="utf-8"))
    exporter = ExcelExporter(tmp_path)
    workbook_path = exporter.export(payload, filename="contract_audit.xlsx")

    assert_excel_columns(
        workbook_path,
        "Audit Summary",
        [
            "total_stories",
            "total_commits",
            "stories_with_commits",
            "stories_without_commits",
            "orphan_commits",
            "generated_at",
            "timezone",
        ],
    )
    assert_excel_columns(
        workbook_path,
        "Stories Without Commits",
        ["key", "fields.summary"],
    )
    assert_excel_columns(
        workbook_path,
        "Orphan Commits",
        ["hash", "message", "author", "date", "repository", "branch"],
    )
    assert_excel_columns(
        workbook_path,
        "Commit Mapping",
        [
            "story_key",
            "story_summary",
            "commit_hash",
            "commit_message",
            "commit_author",
            "commit_date",
            "repository",
            "branch",
        ],
    )
