from __future__ import annotations

from matcher.engine import match


def test_matcher_links_commits_using_priority_sources() -> None:
    issues = [
        {"key": "APP-1", "fields": {"summary": "First story"}},
        {"key": "APP-2", "fields": {"summary": "Second story"}},
    ]
    commits = [
        {
            "hash": "c1",
            "message": "app-1 fix",
            "branch": "feature/app-2-cleanup",
            "pull_request": {"title": "APP-9 fallback"},
        },
        {
            "hash": "c2",
            "message": "no story references here",
        },
        {
            "hash": "c3",
            "story_keys": ["app-2", "APP-2", "OPS-1"],
            "message": "OPS-1 adjust",
        },
    ]

    matched, missing, orphans, summary = match(issues, commits)

    linked_pairs = {(entry["issue_key"], entry["commit"]["hash"]) for entry in matched}
    assert linked_pairs == {
        ("APP-1", "c1"),
        ("APP-2", "c1"),
        ("APP-9", "c1"),
        ("APP-2", "c3"),
        ("OPS-1", "c3"),
    }

    assert [story.get("key") for story in missing] == []
    assert {commit.get("hash") for commit in orphans} == {"c2"}

    assert summary["total_commits"] == 3
    assert summary["total_issues"] == 2
    assert summary["orphan_commits"] == 1
