"""Command line utilities for ReleaseCopilot automation hooks."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from clients.bitbucket_client import BitbucketClient
from config.settings import load_settings
from releasecopilot.ingest.bitbucket_scanner import BitbucketScanner
from releasecopilot.ingest.storage import CommitStorage
from releasecopilot.logging_config import configure_logging
from releasecopilot.utils.coverage import enforce_threshold
from releasecopilot.utils.coverage_comment import COMMENT_MARKER, build_comment


def _github_request(
    method: str,
    url: str,
    token: str,
    data: MutableMapping[str, object] | None = None,
) -> Mapping[str, object]:
    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")

    request = Request(url, data=payload, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    if payload is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urlopen(request) as response:
            content = response.read().decode("utf-8")
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API error {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"GitHub API connection failure: {error}") from error

    parsed = json.loads(content)
    if isinstance(parsed, Mapping):
        return parsed
    if isinstance(parsed, list):  # type: ignore[return-value]
        return {"items": parsed}
    raise RuntimeError("Unexpected payload from GitHub API")


def _find_existing_comment(
    items: Iterable[Mapping[str, object]],
) -> Mapping[str, object] | None:
    for item in items:
        body = item.get("body")
        if isinstance(body, str) and COMMENT_MARKER in body:
            return item
    return None


def _sync_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    base_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    response = _github_request("GET", base_url, token)
    items = response.get("items")
    if not isinstance(items, list):
        raise RuntimeError("GitHub API did not return a comment list")

    existing = _find_existing_comment(item for item in items)
    if existing is not None:
        url = existing.get("url")
        if not isinstance(url, str):
            raise RuntimeError("Existing comment is missing a URL")
        _github_request("PATCH", url, token, {"body": body})
    else:
        _github_request("POST", base_url, token, {"body": body})


def _parse_event(event_path: Path) -> Mapping[str, object]:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("GitHub event payload must be a JSON object")
    return payload


def _extract_pr_number(event: Mapping[str, object]) -> int:
    number = event.get("number")
    if isinstance(number, int):
        return number
    raise ValueError("Pull request number missing from event payload")


def _add_pr_comment_parser(subparsers) -> None:
    pr_comment = subparsers.add_parser(
        "pr-comment", help="Post ReleaseCopilot comments to GitHub PR threads"
    )
    pr_sub = pr_comment.add_subparsers(dest="topic", required=True)

    coverage = pr_sub.add_parser("coverage", help="Publish pytest coverage results as a PR comment")
    coverage.add_argument(
        "--file",
        dest="report",
        type=Path,
        required=True,
        help="Path to the coverage report (coverage.json or coverage.xml)",
    )
    coverage.add_argument(
        "--minimum",
        dest="minimum",
        type=float,
        default=70.0,
        help="Coverage percentage threshold (default: 70.0)",
    )
    coverage.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub token (defaults to GITHUB_TOKEN)",
    )
    coverage.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="Full repository slug, e.g. org/repo (defaults to GITHUB_REPOSITORY)",
    )
    coverage.add_argument(
        "--pr-number",
        dest="pr_number",
        type=int,
        help="Pull request number (defaults to event payload)",
    )
    coverage.add_argument(
        "--event-path",
        dest="event_path",
        type=Path,
        default=os.environ.get("GITHUB_EVENT_PATH"),
        help="Path to the GitHub event payload (defaults to GITHUB_EVENT_PATH)",
    )
    coverage.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the comment without calling the GitHub API",
    )
    coverage.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Optional list of paths to scope coverage gating",
    )


def _add_ingest_parser(subparsers) -> None:
    ingest = subparsers.add_parser("ingest", help="Ingestion utilities")
    ingest_sub = ingest.add_subparsers(dest="topic", required=True)

    scan = ingest_sub.add_parser(
        "bitbucket-scan",
        help="Run a Phoenix-aware Bitbucket commit scan and persist results",
    )
    scan.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional override configuration file (defaults to config/settings.yaml)",
    )
    scan.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Time window (in hours) to include in the scan",
    )
    scan.add_argument(
        "--repos",
        nargs="*",
        default=None,
        help="Repositories to scan (defaults to configuration)",
    )
    scan.add_argument(
        "--branches",
        nargs="*",
        default=None,
        help="Optional branches to include (defaults to configuration)",
    )
    scan.add_argument(
        "--database",
        type=Path,
        default=Path("data/bitbucket/commits.db"),
        help="SQLite database used for commit persistence",
    )
    scan.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/issues/wave3/bitbucket"),
        help="Directory for run metadata artifacts",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_pr_comment_parser(subparsers)
    _add_ingest_parser(subparsers)
    return parser


def _handle_pr_comment_coverage(args: argparse.Namespace) -> str:
    totals = enforce_threshold(args.report, args.minimum, include=args.paths)
    comment = build_comment(totals.percent, minimum=args.minimum, paths=tuple(args.paths or ()))

    if args.dry_run:
        print(comment)
        return comment

    token = args.token
    repo = args.repo

    if not token:
        raise SystemExit("GitHub token is required (pass --token or set GITHUB_TOKEN)")
    if not repo:
        raise SystemExit("Repository slug is required (pass --repo or set GITHUB_REPOSITORY)")

    pr_number = args.pr_number
    if pr_number is None:
        if args.event_path is None:
            raise SystemExit("--pr-number or --event-path must be provided")
        event = _parse_event(args.event_path)
        pr_number = _extract_pr_number(event)

    _sync_comment(token, repo, pr_number, comment)
    print(comment)
    return comment


def _handle_ingest_bitbucket_scan(args: argparse.Namespace) -> dict[str, object]:
    settings = load_settings(path=args.config)
    bitbucket_cfg = settings.get("bitbucket", {}) if isinstance(settings, dict) else {}

    workspace = bitbucket_cfg.get("workspace")
    if not workspace:
        raise SystemExit("Bitbucket workspace is not configured")

    credentials = bitbucket_cfg.get("credentials", {}) if isinstance(bitbucket_cfg, dict) else {}

    cache_root = Path("temp_data") / "bitbucket"
    client = BitbucketClient(
        workspace=workspace,
        username=credentials.get("username"),
        app_password=credentials.get("app_password"),
        access_token=credentials.get("access_token"),
        cache_dir=cache_root,
    )

    repositories_cfg = args.repos or bitbucket_cfg.get("repositories") or []
    if isinstance(repositories_cfg, str):
        repositories = [repositories_cfg]
    elif isinstance(repositories_cfg, Sequence):
        repositories = [str(repo) for repo in repositories_cfg]
    else:
        repositories = []

    if not repositories:
        raise SystemExit("No Bitbucket repositories configured")

    branches_cfg = args.branches or bitbucket_cfg.get("default_branches") or None
    if branches_cfg is None:
        branches_tuple: tuple[str, ...] | None = None
    elif isinstance(branches_cfg, str):
        branches_tuple = (branches_cfg,)
    elif isinstance(branches_cfg, Sequence):
        branches_tuple = tuple(str(branch) for branch in branches_cfg)
    else:
        raise SystemExit("Configured branches must be a sequence of strings")

    storage = CommitStorage(args.database)
    scanner = BitbucketScanner(
        client=client,
        storage=storage,
        artifact_dir=args.artifact_dir,
    )

    result = scanner.scan(
        repos=repositories,
        hours=args.hours,
        branches=branches_tuple,
    )

    commits_obj = result.get("commits")
    if not isinstance(commits_obj, list):
        raise RuntimeError("Bitbucket scanner returned an unexpected commits payload")

    window_start_obj = result.get("window_start")
    window_end_obj = result.get("window_end")
    if not isinstance(window_start_obj, datetime) or not isinstance(window_end_obj, datetime):
        raise RuntimeError("Bitbucket scanner returned invalid window bounds")

    artifact_path_obj = result.get("artifact_path")
    if not isinstance(artifact_path_obj, Path):
        raise RuntimeError("Bitbucket scanner returned an invalid artifact path")

    summary = {
        "artifact": str(artifact_path_obj),
        "commit_count": len(commits_obj),
        "window": {
            "start": window_start_obj.isoformat(),
            "end": window_end_obj.isoformat(),
            "hours": args.hours,
        },
    }
    print(json.dumps(summary, indent=2))
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(os.environ.get("LOG_LEVEL", "INFO"))

    if args.command == "pr-comment" and args.topic == "coverage":
        _handle_pr_comment_coverage(args)
        return 0
    if args.command == "ingest" and args.topic == "bitbucket-scan":
        _handle_ingest_bitbucket_scan(args)
        return 0

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
