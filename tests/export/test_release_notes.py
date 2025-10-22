"""Tests for release note grouping helpers."""

from __future__ import annotations

from export.release_notes import (
    flatten_grouped_notes,
    group_release_notes,
    serialise_grouped_notes,
)


def test_group_release_notes_groups_by_issue_type() -> None:
    issues = [
        {
            "key": "APP-1",
            "summary": "Add login endpoint",
            "issue_type": "Story",
            "uri": "https://example.invalid/browse/APP-1",
        },
        {
            "key": "APP-2",
            "summary": "Fix regression",
            "issue_type": "Bug",
            "uri": "https://example.invalid/browse/APP-2",
        },
        {
            "key": "APP-3",
            "fields": {"summary": "Story with fallback"},
            "labels": ["Enhancement"],
        },
    ]

    grouped = group_release_notes(issues, base_url="https://example.invalid")

    assert set(grouped.keys()) == {"Story", "Bug", "Enhancement"}
    assert [note.issue_key for note in grouped["Story"]] == ["APP-1"]
    assert [note.issue_key for note in grouped["Bug"]] == ["APP-2"]
    assert [note.url for note in grouped["Enhancement"]] == [
        "https://example.invalid/browse/APP-3"
    ]

    serialised = serialise_grouped_notes(grouped)
    assert serialised["Story"][0]["summary"] == "Add login endpoint"

    flattened = flatten_grouped_notes(grouped)
    change_types = {row["change_type"] for row in flattened}
    assert change_types == {"Story", "Bug", "Enhancement"}
