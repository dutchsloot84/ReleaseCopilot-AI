"""Compatibility shim that exposes the src-based package."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_PACKAGE_DIR = Path(__file__).resolve().parent
_SRC_PACKAGE_DIR = _PACKAGE_DIR.parent / "src" / "ops"


def _bootstrap_src_package() -> None:
    if not _SRC_PACKAGE_DIR.exists():
        return

    spec = importlib.util.spec_from_file_location(
        __name__,
        _SRC_PACKAGE_DIR / "__init__.py",
        submodule_search_locations=[str(_SRC_PACKAGE_DIR)],
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive guard
        return

    module = importlib.util.module_from_spec(spec)
    sys.modules[__name__] = module
    sys.modules.setdefault("src.ops", module)
    spec.loader.exec_module(module)
    globals().update(module.__dict__)


_bootstrap_src_package()
