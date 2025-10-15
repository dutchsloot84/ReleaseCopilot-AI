"""GitHub helper clients for Git Historian."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import check_comment_permissions
from .projects_v2 import ProjectStatusItem, ProjectsV2Client

if TYPE_CHECKING:  # pragma: no cover - import only for typing
    from click import Command as _ClickCommand

_WAVE2_HELPER_CLI = None


def wave2_helper_cli() -> "_ClickCommand":
    """Return the Wave 2 helper CLI command."""

    global _WAVE2_HELPER_CLI
    if _WAVE2_HELPER_CLI is None:
        from .wave2_helper import cli

        _WAVE2_HELPER_CLI = cli
    return _WAVE2_HELPER_CLI

__all__ = [
    "ProjectStatusItem",
    "ProjectsV2Client",
    "check_comment_permissions",
    "wave2_helper_cli",
]
