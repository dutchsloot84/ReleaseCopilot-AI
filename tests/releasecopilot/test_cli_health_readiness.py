"""Tests for the ``rc health readiness`` command."""

from __future__ import annotations

from typing import Dict

import pytest

from releasecopilot.cli import health


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("SECRET_JIRA", "SECRET_BITBUCKET", "SECRET_WEBHOOK"):
        monkeypatch.delenv(key, raising=False)


def test_readiness_reports_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for key, name in {
        "SECRET_JIRA": "releasecopilot/jira/oauth",
        "SECRET_BITBUCKET": "releasecopilot/bitbucket/token",
        "SECRET_WEBHOOK": "releasecopilot/jira/webhook_secret",
    }.items():
        monkeypatch.setenv(key, name)

    monkeypatch.setattr(health, "get_secret", lambda name: {"id": name})

    exit_code = health.main(["readiness", "--log-level", "WARNING"])

    assert exit_code == 0
    output = capsys.readouterr().out.strip().splitlines()
    assert "OK SECRET_JIRA" in output
    assert "OK SECRET_BITBUCKET" in output
    assert "OK SECRET_WEBHOOK" in output


def test_readiness_handles_missing_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SECRET_BITBUCKET", "releasecopilot/bitbucket/token")

    exit_code = health.main(["readiness"])

    assert exit_code == 1
    output = capsys.readouterr().out.strip().splitlines()
    assert "FAIL SECRET_JIRA (missing environment variable)" in output[0]


def test_readiness_handles_secret_lookup_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SECRET_JIRA", "releasecopilot/jira/oauth")
    monkeypatch.setenv("SECRET_BITBUCKET", "releasecopilot/bitbucket/token")
    monkeypatch.setenv("SECRET_WEBHOOK", "releasecopilot/jira/webhook_secret")

    def _fake_get_secret(name: str) -> Dict[str, str] | None:
        return None if "bitbucket" in name else {"id": name}

    monkeypatch.setattr(health, "get_secret", _fake_get_secret)

    exit_code = health.main(["readiness"])

    assert exit_code == 1
    output = capsys.readouterr().out.strip().splitlines()
    assert any(line.startswith("FAIL SECRET_BITBUCKET") for line in output)
