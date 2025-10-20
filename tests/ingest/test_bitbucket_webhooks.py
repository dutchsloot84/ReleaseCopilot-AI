from __future__ import annotations

import json
from pathlib import Path
from zoneinfo import ZoneInfo

from releasecopilot.ingest.bitbucket_webhooks import (
    BitbucketWebhookHandler,
    extract_story_keys,
    handle_push,
)
from releasecopilot.ingest.storage import CommitStorage

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "bitbucket"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_handle_push_extracts_story_keys() -> None:
    event = load_fixture("push_event.json")
    commits = handle_push(event)

    hashes = {commit.hash for commit in commits}
    assert hashes == {"abc123", "def456"}

    first = next(commit for commit in commits if commit.hash == "abc123")
    assert first.story_keys == ("RC-123",)
    assert first.files_changed == ("src/app.py", "README.md")
    assert first.authorship == "Alice <alice@example.com>"

    second = next(commit for commit in commits if commit.hash == "def456")
    assert second.story_keys == ("RC-124", "RC-123")
    assert second.authorship == "Bob"


def test_handle_pull_request_deduplicates_commits(tmp_path: Path) -> None:
    payload = load_fixture("pr_event.json")
    storage = CommitStorage(tmp_path / "commits.db", tz=ZoneInfo("America/Phoenix"))
    handler = BitbucketWebhookHandler(
        storage=storage,
        secret="super-secret",
        tz=ZoneInfo("America/Phoenix"),
    )

    status, body = handler.process(payload, headers={"X-Webhook-Secret": "super-secret"})
    assert status == 202
    assert body == {"ok": True, "ingested": 1}
    assert storage.fetch_hashes() == {"123abc"}

    status, body = handler.process(payload, headers={"X-Webhook-Secret": "super-secret"})
    assert status == 202
    assert body == {"ok": True, "ingested": 1}
    assert storage.fetch_hashes() == {"123abc"}


def test_extract_story_keys_prefers_message_then_branch_then_title() -> None:
    keys = extract_story_keys(
        message="fix RC-101",
        branch="feature/rc-102-extra",
        pr_title="RC-103 fallback",
    )
    assert keys == ("RC-101", "RC-102", "RC-103")


def test_handler_rejects_invalid_secret(tmp_path: Path) -> None:
    payload = load_fixture("push_event.json")
    storage = CommitStorage(tmp_path / "commits.db")
    handler = BitbucketWebhookHandler(storage=storage, secret="expected")

    status, body = handler.process(payload, headers={"X-Webhook-Secret": "nope"})
    assert status == 401
    assert body == {"ok": False, "reason": "unauthorized"}
    assert storage.fetch_hashes() == set()
