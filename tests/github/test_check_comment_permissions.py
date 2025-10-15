import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def event_file(tmp_path: Path) -> Path:
    payload = {
        "action": "created",
        "comment": {
            "body": "/orchestrate release",
            "author_association": "MEMBER",
            "user": {"login": "phoenix-dev"},
        },
        "issue": {"number": 277},
    }
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _run_cli(event_path: Path, roles: str, users: str = "", event_name: str = "issue_comment") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_EVENT_PATH": str(event_path),
            "GITHUB_EVENT_NAME": event_name,
            "ALLOWED_ROLES": roles,
            "ALLOWED_USERS": users,
            "PYTHONWARNINGS": "ignore::RuntimeWarning",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "scripts.github.check_comment_permissions"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_allowed_member_dispatch(event_file: Path) -> None:
    result = _run_cli(event_file, roles="MEMBER,TRIAGE")
    assert result.returncode == 0
    assert result.stderr == ""


def test_outside_collaborator_rejected(event_file: Path) -> None:
    payload = json.loads(event_file.read_text(encoding="utf-8"))
    payload["comment"]["author_association"] = "NONE"
    payload["comment"]["user"]["login"] = "outsider"
    event_file.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_cli(event_file, roles="MEMBER,TRIAGE")
    assert result.returncode == 1
    assert "not authorized" in result.stderr


def test_missing_command_is_rejected(event_file: Path) -> None:
    payload = json.loads(event_file.read_text(encoding="utf-8"))
    payload["comment"]["body"] = "Looks good"  # no command
    event_file.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_cli(event_file, roles="MEMBER")
    assert result.returncode == 1
    assert "Command '/orchestrate' not detected" in result.stderr
