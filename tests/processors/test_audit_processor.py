"""Tests for the audit processor coverage and regression safety."""

from __future__ import annotations

from processors.audit_processor import AuditProcessor


def test_audit_processor_processes_commits_and_issues() -> None:
    issues = [
        {"key": "ABC-1", "fields": {"summary": "Story one"}},
        {"key": "XYZ-2", "fields": {"summary": "Story two"}},
    ]
    commits = [
        {"message": "Implements ABC-1", "hash": "1"},
        {"message": "Refs XYZ-2 and ABC-1", "hash": "2"},
        {"message": "No ticket", "hash": "3"},
    ]

    result = AuditProcessor(issues, commits).process()

    assert result.summary["total_stories"] == 2
    assert result.summary["total_commits"] == 3
    assert result.summary["stories_without_commits"] == 0
    assert len(result.orphan_commits) == 1
    keys = {entry["story_key"] for entry in result.commit_story_mapping}
    assert keys == {"ABC-1", "XYZ-2"}
