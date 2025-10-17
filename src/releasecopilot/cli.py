"""Command line interface for Release Copilot configuration."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Optional

from releasecopilot.logging_config import configure_logging, get_logger

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


from .config import build_config


def _candidate_dotenv_paths(source_path: Path) -> list[Path]:
    """Return potential ``.env`` locations ordered by precedence."""

    resolved_source = source_path.resolve()
    package_root = resolved_source.parent
    candidates: list[Path] = []

    repo_root: Path | None = None
    for parent in [package_root, *package_root.parents]:
        marker_pyproject = parent / "pyproject.toml"
        marker_git = parent / ".git"
        if marker_pyproject.exists() or marker_git.exists():
            repo_root = parent
            break

    seen: set[Path] = set()
    if repo_root is not None:
        root_env = repo_root / ".env"
        candidates.append(root_env)
        seen.add(root_env)

    src_root = package_root.parent
    src_env = src_root / ".env"
    if src_env not in seen:
        candidates.append(src_env)
        seen.add(src_env)

    package_env = package_root / ".env"
    if package_env not in seen:
        candidates.append(package_env)

    return candidates


def _find_dotenv_path(source_path: Optional[Path] = None) -> Optional[Path]:
    """Locate the preferred ``.env`` file for the CLI, if any."""

    if source_path is None:
        source_path = Path(__file__)

    for candidate in _candidate_dotenv_paths(source_path):
        if candidate.is_file():
            return candidate
    return None


def find_dotenv_path(source_path: Optional[Path] = None) -> Optional[Path]:
    """Public wrapper around :func:`_find_dotenv_path` for testing."""

    return _find_dotenv_path(source_path)


def _load_local_dotenv() -> Optional[Path]:
    """Best-effort loading of a project-level ``.env`` file."""

    if load_dotenv is None:
        return None

    env_path = _find_dotenv_path()
    if env_path is None:
        return None

    try:  # pragma: no cover - defensive guard around optional dependency
        load_dotenv(dotenv_path=env_path)
    except Exception:
        # Loading environment variables is a convenience for local usage and
        # should never break the CLI if anything goes wrong.
        return None

    return env_path


_load_local_dotenv()


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release Copilot configuration")
    parser.add_argument(
        "--config",
        help="Path to a releasecopilot.yaml file (defaults to ./releasecopilot.yaml if present)",
    )
    parser.add_argument("--fix-version", dest="fix_version", help="Fix version to operate on")
    parser.add_argument(
        "--jira-base",
        dest="jira_base",
        help="Base URL of the Jira instance (e.g. https://example.atlassian.net)",
    )
    parser.add_argument(
        "--bitbucket-base",
        dest="bitbucket_base",
        help="Base URL of the Bitbucket workspace",
    )
    parser.add_argument("--jira-user", dest="jira_user", help="Jira username or email")
    parser.add_argument("--jira-token", dest="jira_token", help="Jira API token or password")
    parser.add_argument(
        "--bitbucket-token",
        dest="bitbucket_token",
        help="Bitbucket access token or app password",
    )
    parser.add_argument(
        "--use-aws-secrets-manager",
        dest="use_aws_secrets_manager",
        action="store_true",
        default=None,
        help="Enable AWS Secrets Manager fallback when secrets are missing",
    )
    parser.add_argument(
        "--no-aws-secrets-manager",
        dest="use_aws_secrets_manager",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    return parser


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments into a namespace."""

    parser = _create_parser()
    return parser.parse_args(argv)


def run(argv: Optional[Iterable[str]] = None) -> dict:
    """Parse arguments and build the resulting configuration dictionary."""

    args = parse_args(argv)
    configure_logging(args.log_level)
    logger = get_logger(__name__)
    logger.debug(
        "CLI arguments parsed",
        extra={"args": {k: v for k, v in vars(args).items() if v is not None}},
    )
    return build_config(args)


__all__ = ["parse_args", "run", "build_config", "find_dotenv_path"]
