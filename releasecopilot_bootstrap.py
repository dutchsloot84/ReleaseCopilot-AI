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
if str(_SRC_DIR) not in sys.path:
    sys.path.append(str(_SRC_DIR))

__all__ = ["_SRC_DIR"]
