"""Shared pytest fixtures for Release Copilot tests."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import sys
import types
from typing import Any, Dict
from zoneinfo import ZoneInfo

import pytest

try:
    from releasecopilot.wave import wave2_helper as generator
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    if exc.name == "jinja2":
        pytest.skip("jinja2 is required for generator tests", allow_module_level=True)
    raise

FIXED_NOW = datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo(generator.PHOENIX_TZ))


@pytest.fixture(scope="session", autouse=True)
def stub_config_settings() -> None:
    """Provide minimal ``config.settings`` defaults for all tests."""

    module = sys.modules.get("config.settings")
    created = False
    if module is None:
        module = types.ModuleType("config.settings")
        sys.modules["config.settings"] = module
        created = True

    original_timezone = getattr(module, "DEFAULT_TIMEZONE", None)
    original_network_flag = getattr(module, "ENABLE_NETWORK", None)

    module.DEFAULT_TIMEZONE = "America/Phoenix"
    module.ENABLE_NETWORK = False

    try:
        yield
    finally:
        if original_timezone is None:
            delattr(module, "DEFAULT_TIMEZONE")
        else:
            module.DEFAULT_TIMEZONE = original_timezone

        if original_network_flag is None:
            delattr(module, "ENABLE_NETWORK")
        else:
            module.ENABLE_NETWORK = original_network_flag

        if created:
            sys.modules.pop("config.settings", None)


@pytest.fixture(scope="session", autouse=True)
def block_network() -> None:
    """Prevent network access during the entire test session."""

    original_socket = socket.socket
    original_create_connection = socket.create_connection

    def _guard(*args: object, **kwargs: object) -> socket.socket:  # type: ignore[override]
        raise RuntimeError("Network access is disabled during tests.")

    socket.socket = _guard  # type: ignore[assignment]
    socket.create_connection = _guard  # type: ignore[assignment]

    try:
        yield
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create_connection


def _copy_templates(dst: Path) -> None:
    template_root = Path(__file__).resolve().parents[1] / "templates"
    for template in ("mop.md.j2", "subprompt.md.j2", "issue_body.md.j2"):
        shutil.copyfile(template_root / template, dst / template)


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

    def __call__(self, path: str | Path) -> Dict[str, Any]:  # pragma: no cover - documentation only
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
