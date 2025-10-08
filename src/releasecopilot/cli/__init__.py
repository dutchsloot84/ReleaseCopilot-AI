"""CLI helpers for ReleaseCopilot."""

from __future__ import annotations

from .._cli_loader import load_cli_module

_cli_module = load_cli_module()
load_dotenv = getattr(_cli_module, "load_dotenv", None)
parse_args = _cli_module.parse_args
run = _cli_module.run
find_dotenv_path = getattr(_cli_module, "find_dotenv_path", None)
_load_local_dotenv = getattr(_cli_module, "_load_local_dotenv", None)
build_config = _cli_module.build_config

__all__ = [
    "load_dotenv",
    "parse_args",
    "run",
    "find_dotenv_path",
    "_load_local_dotenv",
    "build_config",
]
