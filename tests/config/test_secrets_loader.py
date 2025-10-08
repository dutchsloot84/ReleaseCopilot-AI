"""Unit tests for the configuration secrets loader."""

from __future__ import annotations

import types
from typing import Any, Dict

import pytest

from releasecopilot.config import secrets as secret_loader


@pytest.fixture(autouse=True)
def _reset_secret_loader_cache() -> None:
    secret_loader.get_secret.cache_clear()
    secret_loader._client.cache_clear()  # type: ignore[attr-defined]


class _FakeClient:
    def __init__(self, response: Dict[str, Any]):
        self.response = response
        self.calls: list[str] = []

    def get_secret_value(
        self, SecretId: str
    ) -> Dict[str, Any]:  # noqa: N803 - AWS casing
        self.calls.append(SecretId)
        return dict(self.response)


def _patch_boto3(
    monkeypatch: pytest.MonkeyPatch, response: Dict[str, Any]
) -> _FakeClient:
    client = _FakeClient(response)
    namespace = types.SimpleNamespace(client=lambda service: client)
    monkeypatch.setattr(secret_loader, "boto3", namespace)
    return client


def test_get_secret_parses_json_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _patch_boto3(monkeypatch, {"SecretString": '{"token": "value"}'})

    secret = secret_loader.get_secret("releasecopilot/jira/oauth")

    assert secret == {"token": "value"}
    assert client.calls == ["releasecopilot/jira/oauth"]


def test_get_secret_returns_plain_string(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _patch_boto3(monkeypatch, {"SecretString": "plain-token"})

    secret = secret_loader.get_secret("releasecopilot/bitbucket/token")

    assert secret == "plain-token"
    assert client.calls == ["releasecopilot/bitbucket/token"]


def test_get_secret_requires_name() -> None:
    with pytest.raises(ValueError):
        secret_loader.get_secret("")
