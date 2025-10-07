"""CLI helpers for ReleaseCopilot."""

from __future__ import annotations

from .._cli_loader import load_cli_module

_cli_module = load_cli_module()
load_dotenv = getattr(_cli_module, "load_dotenv", None)
parse_args = _cli_module.parse_args
run = _cli_module.run

__all__ = ["load_dotenv", "parse_args", "run"]
