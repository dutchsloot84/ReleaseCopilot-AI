from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.integration
def test_recover_help_succeeds() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "releasecopilot.entrypoints.recover", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()
