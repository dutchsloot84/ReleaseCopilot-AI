"""Compatibility wrapper for the Release Copilot audit CLI."""

from __future__ import annotations

from releasecopilot.entrypoints import audit as _audit_module
from releasecopilot.entrypoints.audit import *  # noqa: F401,F403
from releasecopilot.entrypoints.audit import main as _audit_main

_phoenix_timestamp = _audit_module._phoenix_timestamp

if __name__ == "__main__":  # pragma: no cover - shim for legacy usage
    raise SystemExit(_audit_main())
