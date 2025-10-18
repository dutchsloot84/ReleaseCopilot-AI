"""Time-window Bitbucket commit scans with Phoenix-aware windows."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Sequence
from zoneinfo import ZoneInfo

from clients.bitbucket_client import BitbucketClient
from releasecopilot.logging_config import get_logger

from .storage import CommitStorage, CommitUpsert

LOGGER = get_logger(__name__)
PHOENIX_TZ = ZoneInfo("America/Phoenix")


def _default_git_sha_resolver() -> str | None:
    try:
        import subprocess

        output = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover - defensive
        return None
    return output.decode("utf-8").strip() or None


def scan_commits(
    *,
    client: BitbucketClient,
    repos: Sequence[str],
    hours: int = 24,
    tz: ZoneInfo | None = None,
    now: datetime | None = None,
    branches: Sequence[str] | None = None,
) -> tuple[list[CommitUpsert], datetime, datetime]:
    """Collect commits modified within the Phoenix-aware window."""

    timezone = tz or PHOENIX_TZ
    window_end = (now or datetime.now(tz=timezone)).astimezone(timezone)
    window_start = window_end - timedelta(hours=hours)

    collected: list[CommitUpsert] = []
    seen_hashes: set[str] = set()
    for repo in repos:
        iterator_kwargs = {"repo": repo, "since": window_start}
        if branches:
            iterator_kwargs["branches"] = branches
        for commit in client.iter_commits(**iterator_kwargs):
            commit_hash = commit.get("hash")
            if not commit_hash or commit_hash in seen_hashes:
                continue
            seen_hashes.add(commit_hash)

            file_entries = commit.get("files", []) or []
            files: list[str] = []
            for entry in file_entries:
                if not isinstance(entry, dict):
                    continue
                path = entry.get("path")
                if isinstance(path, str) and path not in files:
                    files.append(path)
            author_payload = commit.get("author") or {}
            authorship = None
            if isinstance(author_payload, dict):
                authorship = author_payload.get("raw") or (
                    (author_payload.get("user") or {}).get("display_name")
                )

            collected.append(
                CommitUpsert(
                    hash=commit_hash,
                    repository=commit.get("repository") or repo,
                    authorship=authorship,
                    files_changed=tuple(files),
                    branch=commit.get("branch"),
                    modified_on=commit.get("date") or commit.get("modified_on"),
                    source="scan",
                )
            )

    return collected, window_start, window_end


class BitbucketScanner:
    """Coordinate Bitbucket scans, persistence, and artifact emission."""

    def __init__(
        self,
        *,
        client: BitbucketClient,
        storage: CommitStorage,
        artifact_dir: Path | str | None = None,
        tz: ZoneInfo | None = None,
        git_sha_resolver: Callable[[], str | None] | None = None,
    ) -> None:
        self.client = client
        self.storage = storage
        self.tz = tz or PHOENIX_TZ
        self.artifact_dir = (
            Path(artifact_dir) if artifact_dir else Path("artifacts/issues/wave3/bitbucket")
        )
        self._resolve_git_sha = git_sha_resolver or _default_git_sha_resolver

    def scan(
        self,
        repos: Sequence[str],
        *,
        hours: int = 24,
        branches: Sequence[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        commits, window_start, window_end = scan_commits(
            client=self.client,
            repos=repos,
            hours=hours,
            tz=self.tz,
            now=now,
            branches=branches,
        )

        if commits:
            self.storage.upsert_many(commits, observed_at=window_end)
        else:
            LOGGER.info(
                "No Bitbucket commits detected in scan window",
                extra={"repos": list(repos), "hours": hours},
            )

        artifact_path = self._write_artifact(
            commits=commits,
            window_start=window_start,
            window_end=window_end,
            repos=repos,
            hours=hours,
        )

        return {
            "commits": commits,
            "artifact_path": artifact_path,
            "window_start": window_start,
            "window_end": window_end,
        }

    def _write_artifact(
        self,
        *,
        commits: Sequence[CommitUpsert],
        window_start: datetime,
        window_end: datetime,
        repos: Sequence[str],
        hours: int,
    ) -> Path:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        run_id = uuid.uuid4().hex
        payload = {
            "run_id": run_id,
            "git_sha": self._resolve_git_sha(),
            "generated_at": window_end.isoformat(),
            "timezone": self.tz.key if hasattr(self.tz, "key") else str(self.tz),
            "window": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
                "hours": hours,
                "repositories": list(repos),
            },
            "payload": [
                {
                    "hash": record.hash,
                    "repository": record.repository,
                    "authorship": record.authorship,
                    "files_changed": list(record.files_changed),
                    "branch": record.branch,
                    "modified_on": record.modified_on,
                    "source": record.source,
                    "story_keys": list(record.story_keys),
                }
                for record in commits
            ],
        }
        destination = self.artifact_dir / f"scan_{run_id}.json"
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        LOGGER.info(
            "Wrote Bitbucket scan artifact",
            extra={"path": str(destination), "count": len(commits)},
        )
        return destination
