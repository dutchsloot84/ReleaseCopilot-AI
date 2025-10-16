"""Shared pytest fixtures for Release Copilot tests."""

from __future__ import annotations

import json
import shutil
import socket
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("jinja2")

from scripts.github import wave2_helper as generator

FIXED_NOW = datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo(generator.PHOENIX_TZ))


def _copy_templates(dst: Path) -> None:
    template_root = Path(__file__).resolve().parents[1] / "templates"
    for template in ("mop.md.j2", "subprompt.md.j2", "issue_body.md.j2"):
        shutil.copyfile(template_root / template, dst / template)


@pytest.fixture(autouse=True)
def _disable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent network access during the test suite.

    Several modules rely on optional network calls (e.g. fetching secrets).
    Tests should never reach out to external services, so we patch the most
    common socket entry points to raise a helpful error if triggered.
    """

    def _guard(*args: object, **kwargs: object) -> socket.socket:  # type: ignore[override]
        raise RuntimeError("Network access is disabled during tests.")

    monkeypatch.setattr(socket, "socket", _guard)
    monkeypatch.setattr(socket, "create_connection", _guard)


@pytest.fixture(autouse=True)
def _mock_secrets_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent real AWS Secrets Manager access during tests.

    The config loader uses ``CredentialStore.get_all_from_secret``; stub it to
    return an empty mapping so tests never reach AWS.
    """

    def _no_secrets(self, arn):
        return {}

    monkeypatch.setattr(
        "clients.secrets_manager.CredentialStore.get_all_from_secret",
        _no_secrets,
        raising=True,
    )


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the shared fixtures directory."""

    return Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def load_json() -> "LoadJSONFn":
    """Helper fixture to load JSON fixtures by filename."""

    def _loader(path: str | Path) -> Dict[str, Any]:
        file_path = Path(path)
        with file_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    return _loader


class LoadJSONFn:
    """Protocol-like helper for typing the ``load_json`` fixture."""

    def __call__(
        self, path: str | Path
    ) -> Dict[str, Any]:  # pragma: no cover - documentation only
        ...


@pytest.fixture()
def generator_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a temporary workspace seeded with generator templates."""

    (tmp_path / "templates").mkdir(parents=True)
    (tmp_path / "backlog").mkdir(parents=True)
    (tmp_path / "docs/mop/archive").mkdir(parents=True)
    (tmp_path / "docs/sub-prompts").mkdir(parents=True)
    (tmp_path / "artifacts/issues").mkdir(parents=True)
    (tmp_path / "artifacts/manifests").mkdir(parents=True)
    _copy_templates(tmp_path / "templates")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(generator, "phoenix_now", lambda: FIXED_NOW)
    return tmp_path


@pytest.fixture()
def sample_spec(generator_env: Path) -> dict[str, Any]:
    """Return a minimal wave spec for generator tests."""

    spec_path = generator_env / "backlog/sample.yaml"
    spec_path.write_text(
        """
wave: 3
purpose: Ensure sample wave for testing
constraints:
  - Respect America/Phoenix scheduling
quality_bar:
  - Maintain ≥70% coverage on generators
sequenced_prs:
  - title: Sample PR
    acceptance:
      - Render mop
      - Render prompts
    notes:
      - Include Phoenix reminder
    labels:
      - wave:wave3
      - testing
""".strip(),
        encoding="utf-8",
    )
    return generator.load_spec(spec_path)
