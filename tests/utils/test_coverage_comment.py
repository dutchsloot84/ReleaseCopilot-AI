"""Tests for Phoenix-aware coverage comment formatting."""

from __future__ import annotations

from datetime import datetime

from zoneinfo import ZoneInfo

from releasecopilot.utils import coverage_comment


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return cls(2025, 10, 17, 8, 0, 0, tzinfo=tz)


def test_build_comment_uses_marker_and_timestamp(monkeypatch) -> None:
    monkeypatch.setattr(coverage_comment, "datetime", _FixedDateTime)

    comment = coverage_comment.build_comment(coverage=87.3, minimum=70.0, paths=("src/foo.py",))

    assert coverage_comment.COMMENT_MARKER in comment
    assert "87.3%" in comment
    assert "70.0%" in comment
    assert "2025-10-17 08:00:00 MST" in comment
    assert '| Files gated | 1 |' in comment


def test_build_comment_respects_custom_timezone(monkeypatch) -> None:
    class _UTCDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls(2025, 10, 17, 15, 30, 0, tzinfo=tz)

    monkeypatch.setattr(coverage_comment, "datetime", _UTCDateTime)

    comment = coverage_comment.build_comment(coverage=90.0, minimum=75.0, tz=ZoneInfo("UTC"))

    assert "90.0%" in comment
    assert "75.0%" in comment
    assert "2025-10-17 15:30:00 UTC" in comment
