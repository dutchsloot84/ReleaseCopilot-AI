"""Helpers for formatting Phoenix-aware coverage summary comments."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")
COMMENT_MARKER = "<!-- releasecopilot:coverage -->"


def build_comment(
    coverage: float,
    *,
    minimum: float = 70.0,
    tz: ZoneInfo | None = None,
    paths: tuple[str, ...] | None = None,
) -> str:
    """Return a Markdown comment summarising coverage results."""

    zone = tz or PHOENIX_TZ
    timestamp = datetime.now(zone).strftime("%Y-%m-%d %H:%M:%S %Z")
    file_count = len(paths) if paths else None
    lines = [
        COMMENT_MARKER,
        "**Decision:** Enforce ≥70% pytest-cov threshold and publish Phoenix-stamped PR summaries.",
        "**Note:** Contributors must run the gate locally to prevent CI failures.",
        "**Action:** Add coverage gate script, update CI runner, and integrate PR coverage comment command.",
        "",
        f"| Metric | Value |",
        f"| --- | --- |",
        f"| Total coverage | {coverage:.1f}% |",
        f"| Threshold | {minimum:.1f}% |",
        f"| Checked | {timestamp} |",
    ]
    if file_count is not None:
        lines.append(f"| Files gated | {file_count} |")
    return "\n".join(lines)


__all__ = ["PHOENIX_TZ", "COMMENT_MARKER", "build_comment"]
