#!/usr/bin/env python3
"""Validate whether an orchestrator slash-command may execute.

This script reads the GitHub event payload referenced by ``GITHUB_EVENT_PATH``
and ensures that the ``/orchestrate`` command was issued by a trusted actor.

Trust is determined entirely via environment variables so the script can run
in test environments without contacting live GitHub services:

``ALLOWED_ROLES``
    Comma-separated list of ``comment.author_association`` values that are
    permitted to execute the command (case-insensitive). Typical values
    include ``MEMBER`` and ``TRIAGE``.
``ALLOWED_USERS``
    Comma-separated list of GitHub user handles that always have access.
``ORCHESTRATOR_COMMAND``
    Optional override of the slash-command to validate. Defaults to
    ``/orchestrate``.

In production we recommend periodically synchronizing these environment
variables from the GitHub REST API (for example via a scheduled job that
creates a file consumed by the workflow). Unit tests intentionally avoid any
network traffic by supplying synthetic payloads and environment variables.
"""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Set


class PermissionError(RuntimeError):
    """Raised when the actor is not authorized to dispatch the orchestrator."""


@dataclass(frozen=True)
class CommentContext:
    """Minimal data extracted from an ``issue_comment`` event."""

    body: str
    login: str | None
    association: str | None


def _load_event(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"GitHub event payload not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _split_env(value: str | None) -> Set[str]:
    if not value:
        return set()
    return {item.strip().upper() for item in value.split(",") if item.strip()}


def _extract_comment(payload: dict) -> CommentContext:
    comment = payload.get("comment") or {}
    user = comment.get("user") or {}
    return CommentContext(
        body=str(comment.get("body", "")),
        login=user.get("login"),
        association=(comment.get("author_association") or "").upper(),
    )


def _command_in_comment(body: str, command: str) -> bool:
    pattern = re.compile(rf"^\s*{re.escape(command)}\b", re.IGNORECASE | re.MULTILINE)
    return bool(pattern.search(body or ""))


def _is_allowed(
    ctx: CommentContext, allowed_users: Iterable[str], allowed_roles: Iterable[str]
) -> bool:
    login = (ctx.login or "").upper()
    association = (ctx.association or "").upper()
    normalized_users = {user.upper() for user in allowed_users}
    normalized_roles = {role.upper() for role in allowed_roles}
    return bool(login and login in normalized_users) or bool(
        association and association in normalized_roles
    )


def _validate_issue_comment(
    event: dict, allowed_roles: Set[str], allowed_users: Set[str], command: str
) -> None:
    ctx = _extract_comment(event)
    if not _command_in_comment(ctx.body, command):
        raise PermissionError(f"Command '{command}' not detected in comment body.")

    if not _is_allowed(ctx, allowed_users, allowed_roles):
        actor = ctx.login or "unknown"
        association = ctx.association or "unauthenticated"
        raise PermissionError(
            f"GitHub user '{actor}' with association '{association}' is not authorized to run {command}."
        )


def main() -> None:
    event_path_env = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path_env:
        raise ValueError("GITHUB_EVENT_PATH environment variable is required")

    event_path = Path(event_path_env)
    payload = _load_event(event_path)

    event_name = os.environ.get("GITHUB_EVENT_NAME", "").lower()
    command = os.environ.get("ORCHESTRATOR_COMMAND", "/orchestrate")

    allowed_roles = _split_env(os.environ.get("ALLOWED_ROLES"))
    allowed_users = _split_env(os.environ.get("ALLOWED_USERS"))

    # If no roles or users are configured we fail closed.
    if not allowed_roles and not allowed_users:
        raise PermissionError(
            "No allowed roles or users configured for orchestrator dispatch."
        )

    if event_name == "issue_comment":
        _validate_issue_comment(payload, allowed_roles, allowed_users, command)
    else:
        # Other events (e.g. workflow_dispatch) are trusted entrypoints because
        # they require explicit repository permissions to trigger.
        return


if __name__ == "__main__":
    try:
        main()
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
