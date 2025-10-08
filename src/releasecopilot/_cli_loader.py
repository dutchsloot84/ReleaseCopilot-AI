"""Internal helpers for loading the CLI module without circular imports."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_CLI_CACHE_KEY = "releasecopilot._cli_module"


def load_cli_module() -> ModuleType:
    """Return the cached CLI module, loading it if necessary."""

    module = sys.modules.get(_CLI_CACHE_KEY)
    if module is not None:
        return module

    spec = importlib.util.spec_from_file_location(
        _CLI_CACHE_KEY, Path(__file__).with_name("cli.py")
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive branch
        raise ImportError("releasecopilot.cli module could not be loaded")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[_CLI_CACHE_KEY] = module
    return module


__all__ = ["load_cli_module"]
