from __future__ import annotations

from pathlib import Path

import pytest

from tools.generator import generator


@pytest.mark.integration
def test_load_spec_without_pyyaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generator, "yaml", None)
    spec = generator.load_spec(Path("backlog/wave3.yaml"))
    assert spec["wave"] == 3
    assert spec["sequenced_prs"], "expected sequenced PRs to be populated"
    assert spec["constraints"]
