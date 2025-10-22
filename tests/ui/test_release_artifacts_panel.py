"""Tests for the release artifacts Streamlit component."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types

import pytest


class _StreamlitStub:
    def __init__(self) -> None:
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.downloads: list[tuple[str, str, str]] = []
        self.warnings: list[str] = []

    def markdown(self, text: str, **_: object) -> None:
        self.markdowns.append(text)

    def caption(self, text: str, **_: object) -> None:
        self.captions.append(text)

    def download_button(self, label: str, *, data: bytes, file_name: str, mime: str) -> bool:
        self.downloads.append((label, file_name, mime))
        return True

    def warning(self, text: str, **_: object) -> None:
        self.warnings.append(text)


@pytest.fixture()
def component_context(monkeypatch: pytest.MonkeyPatch) -> tuple[_StreamlitStub, types.ModuleType]:
    stub = _StreamlitStub()
    module = types.SimpleNamespace(
        markdown=stub.markdown,
        caption=stub.caption,
        download_button=stub.download_button,
        warning=stub.warning,
    )
    monkeypatch.setitem(sys.modules, "streamlit", module)
    component = importlib.reload(importlib.import_module("ui.components.artifacts"))
    return stub, component


def test_panel_disables_buttons_when_missing(
    tmp_path: Path, component_context: tuple[_StreamlitStub, types.ModuleType]
) -> None:
    stub, component = component_context
    component.render_release_artifacts_panel(base_dir=tmp_path)
    assert stub.downloads == []
    assert any("Release artifacts" in caption for caption in stub.captions)


def test_panel_enables_downloads(
    tmp_path: Path, component_context: tuple[_StreamlitStub, types.ModuleType]
) -> None:
    stub, component = component_context
    release_dir = tmp_path / "release_notes"
    release_dir.mkdir()
    json_path = release_dir / "latest.json"
    json_path.write_text("{}", encoding="utf-8")
    excel_path = release_dir / "latest.xlsx"
    excel_path.write_bytes(b"excel")

    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()
    (validation_dir / "latest.json").write_text("{}", encoding="utf-8")

    component.render_release_artifacts_panel(base_dir=tmp_path)

    labels = {entry[0] for entry in stub.downloads}
    assert "Download release notes (JSON)" in labels
    assert any(name.endswith(".json") for _, name, _ in stub.downloads)
