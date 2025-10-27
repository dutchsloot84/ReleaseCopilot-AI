"""Integration smoke tests for package importability via subprocess."""

from __future__ import annotations

import subprocess
import sys


def test_recover_help_succeeds() -> None:
    """Ensure the recover entrypoint is importable via -m invocation."""

    completed = subprocess.run(
        [sys.executable, "-m", "releasecopilot.entrypoints.recover", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
