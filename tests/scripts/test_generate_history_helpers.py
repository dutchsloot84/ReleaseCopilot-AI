"""Exercise lightweight helpers in ``scripts.generate_history`` for coverage."""

from __future__ import annotations

import datetime as dt

import pytest

import scripts.generate_history as gh


def test_parse_github_datetime_normalizes_to_utc() -> None:
    parsed = gh._parse_github_datetime("2024-05-01T12:34:56Z")
    assert parsed is not None
    assert parsed.tzinfo == dt.timezone.utc
    assert parsed.isoformat() == "2024-05-01T12:34:56+00:00"


def test_validate_window_raises_for_invalid_range() -> None:
    since = dt.datetime(2024, 1, 2, tzinfo=dt.timezone.utc)
    until = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
    with pytest.raises(ValueError):
        gh._validate_window(since, until)


def test_format_helpers_render_expected_strings() -> None:
    issue = gh.Issue(
        number=42,
        title="Improve coverage",
        url="https://example.invalid/issue/42",
        closed_at=None,
        assignees=["octocat"],
        labels=["bug"],
        status="Done",
    )
    pr = gh.PullRequest(
        number=100,
        title="Add feature",
        url="https://example.invalid/pull/100",
        merged_at=dt.datetime(2024, 2, 1, tzinfo=dt.timezone.utc),
        author="octocat",
    )
    issue_line = gh._format_issue(issue, include_status=True)
    assert "Issue [#42]" in issue_line
    assert "Status: Done" in issue_line
    pr_line = gh._format_pr(pr)
    assert "PR [#100]" in pr_line
    assert "by @octocat" in pr_line

    section = gh.SectionResult(entries=[issue_line, pr_line], filters=["filter"], metadata={})
    rendered = gh._render_section(section, "no items")
    assert issue_line in rendered
    empty_rendered = gh._render_section(
        gh.SectionResult(entries=[], filters=[], metadata={}), "none"
    )
    assert "none" in empty_rendered
