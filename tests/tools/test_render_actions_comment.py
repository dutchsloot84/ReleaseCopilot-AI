from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest
from tools import render_actions_comment


@pytest.fixture(autouse=True)
def _freeze_git_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(render_actions_comment, "resolve_git_sha", lambda explicit: "test-sha")


def test_build_comment_with_actions() -> None:
    actions = [
        render_actions_comment.PendingAction(
            wave="Wave 1",
            pr="#2",
            action="Approve",
            owner="John",
            status="Pending",
            due="2025-10-15",
            stack="Budget",
            artifact="infra/file.py",
            labels=["human-action", "wave:1"],
        )
    ]
    body = render_actions_comment.build_comment(actions, actions, pr_number=2, git_sha="abc123")
    assert "Approve" in body
    assert "infra/file.py" in body
    assert "⚠️ Outstanding Human Actions" in body


def test_build_comment_without_matching_actions() -> None:
    actions: List[render_actions_comment.PendingAction] = []
    body = render_actions_comment.build_comment(actions, actions, pr_number=5, git_sha="abc123")
    assert "No outstanding human actions" in body


def test_main_updates_comment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    actions_path = tmp_path / "actions.json"
    actions_path.write_text(
        json.dumps(
            [
                {
                    "wave": "Wave 1",
                    "pr": "#7",
                    "action": "Verify",
                    "owner": "Alex",
                    "status": "Pending",
                    "due": "2025-05-01",
                    "stack": "Budget",
                    "artifact": "infra/file.py",
                    "labels": ["human-action", "wave:1"],
                },
                {
                    "wave": "Wave 1",
                    "pr": "#99",
                    "action": "Other",
                    "owner": "Casey",
                    "status": "Pending",
                    "due": "2025-05-02",
                    "stack": "Ops",
                    "artifact": "ops/file.py",
                    "labels": ["human-action"],
                },
            ]
        ),
        encoding="utf-8",
    )

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"number": 7}), encoding="utf-8")

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/repo")

    calls: List[Dict[str, Any]] = []

    def fake_request(method: str, url: str, token: str, data: Dict[str, Any] | None = None) -> Any:
        calls.append({"method": method, "url": url, "data": data})
        if method == "GET":
            return [
                {
                    "id": 1,
                    "body": "<!-- actions-comment --> prior",
                    "url": "https://api.github.com/repos/acme/repo/issues/comments/1",
                }
            ]
        return {}

    monkeypatch.setattr(render_actions_comment, "github_request", fake_request)

    exit_code = render_actions_comment.main(
        [
            "--actions-path",
            str(actions_path),
            "--event-path",
            str(event_path),
        ]
    )

    assert exit_code == 0
    assert any(call["method"] == "PATCH" for call in calls)
    label_call = next(
        call for call in calls if call["method"] == "POST" and call["url"].endswith("/labels")
    )
    assert sorted(label_call["data"]["labels"]) == ["human-action", "wave:1"]
    patch_call = next(call for call in calls if call["method"] == "PATCH")
    assert "Verify" in patch_call["data"]["body"]
    captured = capsys.readouterr()
    assert "test-sha" in captured.out


def test_main_creates_comment_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    actions_path = tmp_path / "actions.json"
    actions_path.write_text("[]", encoding="utf-8")
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"number": 3}), encoding="utf-8")

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/repo")

    calls: List[Dict[str, Any]] = []

    def fake_request(method: str, url: str, token: str, data: Dict[str, Any] | None = None) -> Any:
        calls.append({"method": method, "url": url, "data": data})
        if method == "GET":
            return []
        return {}

    monkeypatch.setattr(render_actions_comment, "github_request", fake_request)

    exit_code = render_actions_comment.main(
        [
            "--actions-path",
            str(actions_path),
            "--event-path",
            str(event_path),
        ]
    )

    assert exit_code == 0
    assert any(call["method"] == "POST" and "/comments" in call["url"] for call in calls)
