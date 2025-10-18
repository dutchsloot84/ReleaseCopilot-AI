"""Lightweight readiness probe for Secrets Manager connectivity."""

from __future__ import annotations

import argparse
import os
from typing import Mapping, Sequence

from releasecopilot.config.secrets import get_secret, safe_log_kv
from releasecopilot.logging_config import configure_logging, get_logger

_SECRET_ENV_VARS = ("SECRET_JIRA", "SECRET_BITBUCKET", "SECRET_WEBHOOK")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rc health", description="ReleaseCopilot health checks")
    subcommands = parser.add_subparsers(dest="command", required=True)

    readiness = subcommands.add_parser(
        "readiness",
        help="Verify that configured Secrets Manager entries are readable",
    )
    readiness.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level for the readiness probe",
    )
    return parser


def _resolve_secret_names(env: Mapping[str, str] | None = None) -> dict[str, str]:
    source = env or os.environ
    return {key: source.get(key, "") for key in _SECRET_ENV_VARS}


def _check_secret(env_key: str, secret_name: str, logger) -> bool:
    if not secret_name:
        logger.error(
            "Secret environment variable missing",
            extra=safe_log_kv(environment_variable=env_key),
        )
        print(f"FAIL {env_key} (missing environment variable)")
        return False

    secret = get_secret(secret_name)
    if secret is None:
        logger.error(
            "Unable to retrieve secret",
            extra=safe_log_kv(environment_variable=env_key, secret_identifier=secret_name),
        )
        print(f"FAIL {env_key} (unavailable)")
        return False

    logger.info(
        "Secret retrieved successfully",
        extra=safe_log_kv(environment_variable=env_key, secret_identifier=secret_name),
    )
    print(f"OK {env_key}")
    return True


def _run_readiness(args: argparse.Namespace) -> int:
    configure_logging(args.log_level)
    logger = get_logger(__name__)

    names = _resolve_secret_names()
    results = [
        _check_secret(env_key, secret_name, logger) for env_key, secret_name in names.items()
    ]
    return 0 if all(results) else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "readiness":
        return _run_readiness(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
