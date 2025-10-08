"""Release Copilot package."""

from __future__ import annotations

from . import aws_secrets, config
from ._cli_loader import load_cli_module

_cli_module = load_cli_module()
parse_args = _cli_module.parse_args
run = _cli_module.run
load_dotenv = getattr(_cli_module, "load_dotenv", None)

__all__ = [
    "aws_secrets",
    "cli",
    "config",
    "load_dotenv",
    "parse_args",
    "run",
]


def __dir__() -> list[str]:  # pragma: no cover - trivial proxy
    dynamic = {"load_dotenv", "parse_args", "run"}
    return sorted(set(globals()) | dynamic)
