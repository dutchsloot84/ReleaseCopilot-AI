from __future__ import annotations

import importlib
import json
from types import ModuleType

import pytest


def _reload_logging(monkeypatch: pytest.MonkeyPatch, **env: str) -> ModuleType:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    module = importlib.import_module("releasecopilot.logging_config")
    return importlib.reload(module)


def test_structured_logging_includes_correlation_id(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("RC_CORR_ID", "test-corr-id")
    monkeypatch.delenv("RC_LOG_JSON", raising=False)
    logging_module = _reload_logging(monkeypatch)
    logging_module.configure_logging("INFO")
    logger = logging_module.get_logger("test.logger")

    logger.info("hello world")

    output = capsys.readouterr().out.strip()
    assert "hello world" in output
    assert "test-corr-id" in output
    assert output.startswith("20")


def test_json_logging_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    logging_module = _reload_logging(monkeypatch, RC_LOG_JSON="true")
    logging_module.configure_logging("INFO")
    logger = logging_module.get_logger("json.logger")

    logger.info("structured message")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["message"] == "structured message"
    assert payload["correlation_id"] == logging_module.get_correlation_id()
    assert payload["run_id"] == logging_module.get_correlation_id()
    assert payload["timezone"] == "America/Phoenix"
    assert payload["generated_at"].endswith("-07:00")


def test_secret_redaction(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("RC_LOG_JSON", raising=False)
    logging_module = _reload_logging(monkeypatch)
    logging_module.configure_logging("DEBUG")
    logger = logging_module.get_logger("redact.logger")

    logger.debug("token value", extra={"api_token": "abc123", "nested": {"secret": "shhh"}})

    output = capsys.readouterr().out
    assert "***REDACTED***" in output
    assert "abc123" not in output
    assert "shhh" not in output
