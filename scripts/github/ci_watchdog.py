"""GitHub CI Watchdog helpers.

This module contains helpers that are consumed by the CI Watchdog
workflow. The functions are intentionally deterministic so that test
fixtures and saved artifacts remain stable between runs.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import requests
from zoneinfo import ZoneInfo


PHOENIX_TZ = ZoneInfo("America/Phoenix")


class WatchdogError(RuntimeError):
    """Raised when the watchdog encounters an unexpected API error."""


def _auth_headers() -> Dict[str, str]:
    token = os.environ.get("ORCHESTRATOR_BOT_TOKEN")
    if not token:
        raise WatchdogError(
            "ORCHESTRATOR_BOT_TOKEN is required for watchdog operations"
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "ci-watchdog",
    }


def _paginate(
    url: str, session: requests.Session, params: Dict[str, str] | None = None
) -> Iterable[dict]:
    next_url = url
    while next_url:
        response = session.get(next_url, params=params)
        if response.status_code >= 400:
            raise WatchdogError(
                f"GitHub API error {response.status_code}: {response.text}"
            )
        payload = response.json()
        if isinstance(payload, dict) and "items" in payload:
            items = payload["items"]
        else:
            items = payload
        yield from items
        next_url = response.links.get("next", {}).get("url")
        params = None  # params only apply to first request


@dataclass(frozen=True)
class FailingCheck:
    name: str
    conclusion: str
    completed_at: str
    html_url: str


@dataclass(frozen=True)
class PullRequestFailure:
    number: int
    title: str
    html_url: str
    head_sha: str
    latest_failure_at: str
    failing_checks: Sequence[FailingCheck]


def collect_failures(repo: str, max_age_hours: int) -> List[PullRequestFailure]:
    """Collect failing checks for recent pull requests.

    Args:
        repo: GitHub repository in the form ``owner/name``.
        max_age_hours: Ignore failures older than this threshold.
    """

    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")

    now = _dt.datetime.now(tz=_dt.timezone.utc)
    max_age = now - _dt.timedelta(hours=max_age_hours)

    session = requests.Session()
    session.headers.update(_auth_headers())

    pulls_url = f"https://api.github.com/repos/{repo}/pulls"
    pulls_params = {
        "state": "open",
        "per_page": "50",
        "sort": "updated",
        "direction": "desc",
    }

    failures: List[PullRequestFailure] = []
    for pull in _paginate(pulls_url, session, pulls_params):
        if pull.get("draft"):
            continue

        head_sha = pull["head"]["sha"]
        check_runs_url = (
            f"https://api.github.com/repos/{repo}/commits/{head_sha}/check-runs"
        )
        failing_checks: List[FailingCheck] = []
        latest_failure_at: _dt.datetime | None = None

        for check in _paginate(check_runs_url, session):
            conclusion = (check.get("conclusion") or "").lower()
            completed_at_raw = check.get("completed_at")
            if not completed_at_raw:
                continue
            completed_at = _dt.datetime.fromisoformat(
                completed_at_raw.replace("Z", "+00:00")
            )
            if completed_at < max_age:
                continue
            if conclusion not in {
                "failure",
                "timed_out",
                "action_required",
                "cancelled",
            }:
                continue

            latest_failure_at = max(latest_failure_at or completed_at, completed_at)
            failing_checks.append(
                FailingCheck(
                    name=check.get("name", "unknown"),
                    conclusion=conclusion,
                    completed_at=completed_at_raw,
                    html_url=check.get("html_url", ""),
                )
            )

        if not failing_checks:
            continue

        failing_checks.sort(key=lambda c: (c.name.lower(), c.completed_at))

        latest_str = (
            latest_failure_at.isoformat().replace("+00:00", "Z")
            if latest_failure_at
            else ""
        )

        failures.append(
            PullRequestFailure(
                number=pull["number"],
                title=pull.get("title", ""),
                html_url=pull.get("html_url", ""),
                head_sha=head_sha,
                latest_failure_at=latest_str,
                failing_checks=tuple(failing_checks),
            )
        )

    return sorted(failures, key=lambda f: f.number)


def render_report(failures: Sequence[PullRequestFailure]) -> str:
    """Render a Markdown report for CI failures."""

    now_phoenix = _dt.datetime.now(tz=PHOENIX_TZ)
    timestamp = now_phoenix.strftime("%Y-%m-%d %H:%M %Z")

    header = f"## CI Watchdog Report – {timestamp}\n"
    if not failures:
        return header + "\nNo failing checks detected. ✅\n"

    lines = [
        header,
        "\n| PR | Title | Check | Completed (UTC) |",
        "| --- | --- | --- | --- |",
    ]
    for failure in failures:
        pr_link = f"[{failure.number}]({failure.html_url})"
        for check in failure.failing_checks:
            lines.append(
                f"| {pr_link} | {failure.title} | {check.name} ({check.conclusion}) | {check.completed_at} |"
            )

    return "\n".join(lines) + "\n"


def should_autofix(event: Dict) -> bool:
    """Determine if the autofix routine should execute for a slash command."""

    comment = event.get("comment") or {}
    body = comment.get("body", "").strip().lower()
    if "/watchdog autofix" not in body:
        return False

    association = (comment.get("author_association") or "").upper()
    if association not in {"MEMBER", "OWNER", "COLLABORATOR"}:
        return False

    issue = event.get("issue") or {}
    if "pull_request" not in issue:
        return False

    labels = {lbl.get("name", "") for lbl in issue.get("labels", [])}
    if "automation" not in {label.lower() for label in labels}:
        return False

    approvals = 0
    pull_request = event.get("pull_request") or {}
    if "approved_review_count" in pull_request:
        approvals = int(pull_request["approved_review_count"])
    else:
        reviews = pull_request.get("reviews", [])
        approvals = sum(
            1 for review in reviews if review.get("state", "").upper() == "APPROVED"
        )

    return approvals > 0


def serialize_failures(failures: Sequence[PullRequestFailure]) -> List[dict]:
    return [asdict(failure) for failure in failures]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI Watchdog helper CLI")
    parser.add_argument(
        "--repo", required=True, help="GitHub repository in owner/name form"
    )
    parser.add_argument("--max-age-hours", type=int, default=24)
    parser.add_argument(
        "--render", action="store_true", help="Render the markdown report"
    )
    parser.add_argument("--output", type=Path, help="Optional path to write the report")
    parser.add_argument(
        "--metrics", type=Path, help="Optional path to write metrics JSON"
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    failures = collect_failures(args.repo, args.max_age_hours)

    if args.render:
        report = render_report(failures)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
        else:
            print(report)

    if args.metrics:
        metrics_payload = {
            "generated_at": _dt.datetime.now(tz=PHOENIX_TZ).isoformat(),
            "failures_scanned": len(failures),
            "autofixes_attempted": 0,
        }
        args.metrics.parent.mkdir(parents=True, exist_ok=True)
        args.metrics.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    status_output = os.environ.get("WATCHDOG_STATUS_OUTPUT")
    if status_output:
        Path(status_output).parent.mkdir(parents=True, exist_ok=True)
        Path(status_output).write_text(
            json.dumps(serialize_failures(failures), indent=2), encoding="utf-8"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FailingCheck",
    "PullRequestFailure",
    "collect_failures",
    "render_report",
    "serialize_failures",
    "should_autofix",
    "WatchdogError",
]
