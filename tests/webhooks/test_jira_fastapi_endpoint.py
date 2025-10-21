from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from types import SimpleNamespace

import pytest

try:  # pragma: no cover - optional dependency guard
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - handled via pytestmark
    FastAPI = None  # type: ignore[assignment]
    TestClient = None  # type: ignore[assignment]

os.environ.setdefault("TABLE_NAME", "jira-sync-tests")
os.environ.setdefault("AWS_REGION", "us-west-2")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

from services.webhooks import jira as webhook_module

pytestmark = pytest.mark.skipif(
    FastAPI is None or TestClient is None,
    reason="fastapi test client is unavailable",
)


def _make_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _payload() -> dict[str, object]:
    return {
        "webhookEvent": "jira:issue_updated",
        "deliveryId": "delivery-99",
        "issue": {
            "id": "1000",
            "key": "MOB-1",
            "fields": {
                "updated": "2024-01-01T12:00:00.000+0000",
                "project": {"key": "MOB"},
            },
        },
    }


def test_fastapi_webhook_accepts_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "topsecret"
    captured: dict[str, object] = {}

    def _recompute(events):
        captured["events"] = list(events)
        return {"artifact_path": "artifact.json"}

    def _handle_upsert(event):
        captured["issue_key"] = event.issue_key
        return {"success": True}

    stub_handler = SimpleNamespace(
        _handle_upsert=_handle_upsert,
        _handle_delete=lambda event: {"success": True},
    )

    monkeypatch.setattr(webhook_module, "_resolve_secret", lambda: secret)
    monkeypatch.setattr(webhook_module, "recompute_correlation", _recompute)
    monkeypatch.setattr(webhook_module, "lambda_handler", stub_handler)

    app = FastAPI()
    webhook_module.register_jira_webhook(app)
    client = TestClient(app)

    payload = _payload()
    body = json.dumps(payload).encode("utf-8")
    signature = _make_signature(body, secret)

    response = client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "X-Atlassian-Signature": signature,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ok"
    assert data["issue_key"] == "MOB-1"
    assert data["correlation_artifact"] == "artifact.json"
    assert data["received_at"].endswith("-07:00")
    events = captured.get("events")
    assert events and events[0].issue_key == "MOB-1"


def test_fastapi_webhook_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "another"
    stub_handler = SimpleNamespace(
        _handle_upsert=lambda event: {"success": True},
        _handle_delete=lambda event: {"success": True},
    )

    monkeypatch.setattr(webhook_module, "_resolve_secret", lambda: secret)
    monkeypatch.setattr(webhook_module, "recompute_correlation", lambda events: {})
    monkeypatch.setattr(webhook_module, "lambda_handler", stub_handler)

    app = FastAPI()
    webhook_module.register_jira_webhook(app)
    client = TestClient(app)

    payload = _payload()
    body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/webhooks/jira",
        content=body,
        headers={
            "X-Atlassian-Webhook-Signature": "invalid",
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 401
