"""Compatibility shim for the recovery CLI (use the console script instead)."""

from __future__ import annotations

from releasecopilot.entrypoints.recover import main

if __name__ == "__main__":  # pragma: no cover - shim for legacy usage
    raise SystemExit(main())
