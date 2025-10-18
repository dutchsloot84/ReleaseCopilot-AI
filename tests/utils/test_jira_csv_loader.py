"""Tests for the Jira CSV fallback loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from releasecopilot.utils.jira_csv_loader import (
    JiraCSVLoaderError,
    load_issues_from_csv,
)


def test_load_issues_from_csv_success(tmp_path: Path) -> None:
    csv_path = tmp_path / "issues.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Issue key,Summary,Status,Assignee,Issue Type",
                "ABC-1,Demo story,In Progress,Ada Lovelace,Story",
            ]
        ),
        encoding="utf-8",
    )

    issues = load_issues_from_csv(csv_path)

    assert len(issues) == 1
    issue = issues[0]
    assert issue["key"] == "ABC-1"
    assert issue["fields"]["summary"] == "Demo story"
    assert issue["fields"]["status"] == {"name": "In Progress"}
    assert issue["fields"]["assignee"] == {"displayName": "Ada Lovelace"}
    assert issue["fields"]["issuetype"] == {"name": "Story"}


def test_load_issues_from_csv_missing_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "issues.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Summary,Status",
                "Missing key,To Do",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(JiraCSVLoaderError) as excinfo:
        load_issues_from_csv(csv_path)

    assert "Issue key" in str(excinfo.value)


def test_load_issues_from_csv_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"

    with pytest.raises(JiraCSVLoaderError) as excinfo:
        load_issues_from_csv(missing)

    assert "CSV file not found" in str(excinfo.value)
