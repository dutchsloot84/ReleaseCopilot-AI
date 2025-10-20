from __future__ import annotations

from datetime import datetime

import pytest

from releasecopilot.jira.webhook_parser import JiraWebhookEvent, normalize_payload


@pytest.fixture
def sample_payload() -> dict:
    return {
        "webhookEvent": "jira:issue_updated",
        "deliveryId": "delivery-42",
        "issue": {
            "id": "1000",
            "key": "MOB-99",
            "fields": {
                "updated": "2024-01-01T12:00:00.000+0000",
                "project": {"key": "MOB"},
            },
        },
        "changelog": {"id": "555"},
        "timestamp": 1704110400000,
    }


def test_normalize_payload_extracts_required_fields(sample_payload: dict) -> None:
    event = normalize_payload(sample_payload)

    assert isinstance(event, JiraWebhookEvent)
    assert event.issue_key == "MOB-99"
    assert event.delivery_id == "delivery-42"
    assert event.changelog["id"] == "555"
    assert event.updated_at.startswith("2024-01-01T12:00:00")
    datetime.fromisoformat(event.updated_at.replace("Z", "+00:00"))
    assert event.issue["key"] == event.issue_key
    assert event.phoenix_timestamp.endswith("-07:00")


def test_normalize_payload_defaults_optional_fields(sample_payload: dict) -> None:
    del sample_payload["changelog"]
    sample_payload["deliveryId"] = None
    sample_payload["timestamp"] = None
    sample_payload["issue"]["fields"].pop("updated")

    event = normalize_payload(sample_payload)

    assert event.changelog == {}
    assert event.delivery_id is None
    assert event.updated_at.endswith("Z")
    assert event.timestamp is None


def test_normalize_payload_requires_issue_key() -> None:
    with pytest.raises(ValueError):
        normalize_payload({"webhookEvent": "jira:issue_updated", "issue": {}})


def test_normalize_payload_rejects_missing_event() -> None:
    with pytest.raises(ValueError):
        normalize_payload({})
