from __future__ import annotations

import pytest

from matcher.link_rules import extract_story_keys, story_keys_from_commit


def test_extract_story_keys_prefers_message_branch_title() -> None:
    keys = extract_story_keys(
        message="fix rc-101 and RC-102",  # lowercase should normalise
        branch="feature/rc-103-cleanup",
        pr_title="RC-104 fallback",
    )
    assert keys == ("RC-101", "RC-102", "RC-103", "RC-104")


@pytest.mark.parametrize(
    "commit,expected",
    [
        (
            {"story_keys": ["rc-201", "RC-201", "APP-3"]},
            ("RC-201", "APP-3"),
        ),
        (
            {
                "message": "update app-10 to use new API",
                "branch": "feature/app-11",
                "pull_request": {"title": "APP-12 ready"},
            },
            ("APP-10", "APP-11", "APP-12"),
        ),
        (
            {
                "summary": "rc-400: chore",
                "metadata": {"pr_title": "RC-401 coverage"},
            },
            ("RC-400", "RC-401"),
        ),
    ],
)
def test_story_keys_from_commit_handles_sources(
    commit: dict[str, object], expected: tuple[str, ...]
) -> None:
    assert story_keys_from_commit(commit) == expected
