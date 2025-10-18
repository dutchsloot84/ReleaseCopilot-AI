"""Application specific exception hierarchy."""

from __future__ import annotations

from typing import Any


class ReleaseCopilotError(RuntimeError):
    """Base exception that carries structured context."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class JiraTokenRefreshError(ReleaseCopilotError):
    """Raised when Jira token refresh fails."""


class JiraQueryError(ReleaseCopilotError):
    """Raised when Jira issue search fails."""


class JiraJQLFailed(JiraQueryError):
    """Raised when Jira JQL searches exhaust retries and still fail."""


class BitbucketRequestError(ReleaseCopilotError):
    """Raised when Bitbucket requests fail."""


__all__ = [
    "ReleaseCopilotError",
    "JiraTokenRefreshError",
    "JiraQueryError",
    "JiraJQLFailed",
    "BitbucketRequestError",
]
