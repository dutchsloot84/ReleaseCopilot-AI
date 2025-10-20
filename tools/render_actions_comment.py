"""Render pending human actions as a sticky GitHub PR comment."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable, List, Optional, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")
COMMENT_MARKER = "<!-- actions-comment -->"
COMMENT_TITLE = "⚠️ Outstanding Human Actions"


@dataclass
class PendingAction:
    wave: str
    pr: str
    action: str
    owner: str
    status: str
    due: str
    stack: str
    artifact: str
    labels: List[str]

    @classmethod
    def from_dict(cls, data: dict) -> "PendingAction":
        return cls(
            wave=data.get("wave", ""),
            pr=data.get("pr", ""),
            action=data.get("action", ""),
            owner=data.get("owner", ""),
            status=data.get("status", ""),
            due=data.get("due", ""),
            stack=data.get("stack", ""),
            artifact=data.get("artifact", ""),
            labels=list(data.get("labels", [])),
        )


def load_actions(path: Path) -> List[PendingAction]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("pending_actions.json must be a list")
    return [PendingAction.from_dict(item) for item in payload]


def resolve_git_sha(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip()


def parse_event(event_path: Path) -> dict:
    return json.loads(event_path.read_text(encoding="utf-8"))


def extract_pr_number(event: dict) -> int:
    try:
        return int(event["number"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Pull request number missing from event payload") from exc


def filter_actions(actions: Iterable[PendingAction], pr_number: int) -> List[PendingAction]:
    needle = f"#{pr_number}"
    return [action for action in actions if action.pr == needle]


def build_comment(
    actions: List[PendingAction],
    all_actions: List[PendingAction],
    pr_number: int,
    git_sha: str,
) -> str:
    timestamp = datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d %H:%M MST")
    header = [COMMENT_MARKER, f"{COMMENT_TITLE}", ""]
    metadata = [
        f"Run metadata (git: `{git_sha}`, args: `{ ' '.join(sys.argv[1:]) or 'default' }`, time: {timestamp}).",
    ]
    body_lines: List[str] = []
    if actions:
        body_lines.append("| Action | Owner | Status | Due (MST) | Stack | Artifact |")
        body_lines.append("|--------|-------|--------|-----------|-------|----------|")
        for item in actions:
            artifact_link = item.artifact or ""
            body_lines.append(
                f"| {item.action} | {item.owner} | {item.status} | {item.due} | {item.stack} | {artifact_link} |"
            )
    else:
        if all_actions:
            body_lines.append(
                f"No outstanding actions for PR #{pr_number}. {len(all_actions)} action(s) tracked for other PRs."
            )
        else:
            body_lines.append("No outstanding human actions tracked.")
    body = "\n".join(header + metadata + [""] + body_lines)
    return body


def github_request(method: str, url: str, token: str, data: Optional[dict] = None) -> dict:
    payload: Optional[bytes] = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
    req = Request(url, data=payload, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API error {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"GitHub API connection failure: {error}") from error


def find_existing_comment(comments: List[dict]) -> Optional[dict]:
    for comment in comments:
        if COMMENT_MARKER in comment.get("body", ""):
            return comment
    return None


def sync_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    comments_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    raw_comments = github_request("GET", comments_url, token, None)
    if not isinstance(raw_comments, list):
        raise RuntimeError("Expected list of comments from GitHub API")
    comments = raw_comments
    existing = find_existing_comment(comments)
    if existing:
        comment_url = existing.get("url")
        if not comment_url:
            raise RuntimeError("Existing comment URL missing")
        github_request("PATCH", comment_url, token, {"body": body})
    else:
        github_request("POST", comments_url, token, {"body": body})


def sync_labels(token: str, repo: str, pr_number: int, actions: Iterable[PendingAction]) -> None:
    labels: List[str] = []
    for item in actions:
        for label in item.labels:
            if label not in labels:
                labels.append(label)
    if not labels:
        return
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels"
    github_request("POST", url, token, {"labels": labels})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actions-path",
        default="actions/pending_actions.json",
        type=Path,
        help="Path to pending actions JSON file.",
    )
    parser.add_argument(
        "--event-path",
        default=os.environ.get("GITHUB_EVENT_PATH"),
        type=Path,
        help="GitHub event payload path.",
    )
    parser.add_argument(
        "--git-sha",
        default=None,
        help="Optional Git SHA override.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")

    git_sha = resolve_git_sha(args.git_sha)
    actions = load_actions(args.actions_path)
    if args.event_path is None:
        raise SystemExit("--event-path or GITHUB_EVENT_PATH is required")
    event = parse_event(args.event_path)
    pr_number = extract_pr_number(event)

    pr_actions = filter_actions(actions, pr_number)
    body = build_comment(pr_actions, actions, pr_number, git_sha)

    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is required")

    sync_comment(token, repo, pr_number, body)
    sync_labels(token, repo, pr_number, pr_actions)

    metadata = {
        "timestamp_mst": datetime.now(PHOENIX_TZ).strftime("%Y-%m-%d %H:%M MST"),
        "git_sha": git_sha,
        "actions_path": str(args.actions_path),
        "pr_number": pr_number,
        "applied_labels": sorted({label for action in pr_actions for label in action.labels}),
        "cli_args": sys.argv[1:],
    }
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
