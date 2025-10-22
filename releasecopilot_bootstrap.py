"""Bootstrap helpers for ReleaseCopilot CLI entry points.

This module ensures that the ``src`` layout used in the repository is added to
``sys.path`` when running scripts directly (e.g., ``python main.py``). Importing
this module has the side effect of registering the ``src`` directory so that
the ``releasecopilot`` package can be resolved without modifying each entry
point individually.
"""

from __future__ import annotations

from pathlib import Path
import sys

_SRC_DIR = Path(__file__).resolve().parent / "src"
_SRC_STR = str(_SRC_DIR)
while _SRC_STR in sys.path:
    sys.path.remove(_SRC_STR)
sys.path.insert(0, _SRC_STR)

__all__ = ["_SRC_DIR"]
