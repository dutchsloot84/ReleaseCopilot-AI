"""Smoke tests ensuring CLI modules import without side effects."""

from __future__ import annotations

import importlib

MODULES: tuple[str, ...] = (
    "cli.app",
    "cli.audit",
    "cli.health",
    "export.exporter",
    "releasecopilot.entrypoints.audit",
    "releasecopilot.entrypoints.recover",
    "releasecopilot.entrypoints.wave2",
    "releasecopilot.orchestrator.release_exports",
)


def test_cli_modules_import_cleanly() -> None:
    """Each CLI module should import without raising exceptions."""

    failures: list[tuple[str, Exception]] = []
    for module_name in MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - failure path is logged
            failures.append((module_name, exc))

    if failures:
        messages = ", ".join(f"{name}: {error}" for name, error in failures)
        raise AssertionError(f"Failed to import modules: {messages}")
