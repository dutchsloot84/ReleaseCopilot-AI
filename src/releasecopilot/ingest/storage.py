"""Persistence helpers for Bitbucket commit ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
import json
from pathlib import Path
import sqlite3
from typing import Iterable, Sequence

from releasecopilot.logging_config import get_logger

LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class CommitUpsert:
    """Normalized representation of a Bitbucket commit for storage."""

    hash: str
    repository: str
    authorship: str | None
    files_changed: Sequence[str]
    story_keys: Sequence[str] = ()
    source: str = "scan"
    branch: str | None = None
    modified_on: str | None = None


class CommitStorage:
    """SQLite-backed persistence layer with idempotent upsert semantics."""

    def __init__(self, path: Path | str, *, tz: tzinfo | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._tz = tz or timezone.utc
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bitbucket_commits (
                    hash TEXT PRIMARY KEY,
                    repository TEXT NOT NULL,
                    authorship TEXT,
                    files_changed TEXT NOT NULL,
                    story_keys TEXT,
                    source TEXT NOT NULL,
                    branch TEXT,
                    modified_on TEXT,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def upsert_many(
        self,
        records: Iterable[CommitUpsert],
        *,
        observed_at: datetime | None = None,
    ) -> int:
        """Persist commits using INSERT OR REPLACE semantics."""

        commits = list(records)
        if not commits:
            return 0

        observed = observed_at or datetime.now(tz=self._tz)
        observed_iso = observed.astimezone(timezone.utc).isoformat()

        payloads = [
            (
                record.hash,
                record.repository,
                record.authorship,
                json.dumps(list(dict.fromkeys(record.files_changed))),
                json.dumps(list(dict.fromkeys(record.story_keys))),
                record.source,
                record.branch,
                record.modified_on,
                observed_iso,
            )
            for record in commits
        ]

        query = """
            INSERT INTO bitbucket_commits (
                hash, repository, authorship, files_changed, story_keys,
                source, branch, modified_on, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(hash) DO UPDATE SET
                repository=excluded.repository,
                authorship=excluded.authorship,
                files_changed=excluded.files_changed,
                story_keys=excluded.story_keys,
                source=excluded.source,
                branch=COALESCE(excluded.branch, bitbucket_commits.branch),
                modified_on=COALESCE(excluded.modified_on, bitbucket_commits.modified_on),
                last_seen_at=excluded.last_seen_at
        """

        with self._connect() as conn:
            conn.executemany(query, payloads)
            conn.commit()

        LOGGER.info(
            "Persisted Bitbucket commits",
            extra={"count": len(payloads), "database": str(self.path)},
        )
        return len(payloads)

    def fetch_hashes(self) -> set[str]:
        """Return the set of commit hashes currently stored (testing helper)."""

        with self._connect() as conn:
            cursor = conn.execute("SELECT hash FROM bitbucket_commits")
            return {row[0] for row in cursor.fetchall()}
