"""Validation document builder tests."""

from __future__ import annotations

from releasecopilot.orchestrator.validation_doc import build_validation_doc


def test_build_validation_doc_uses_configured_field() -> None:
    issues = [
        {
            "key": "APP-1",
            "summary": "First story",
            "uri": "https://example.invalid/browse/APP-1",
            "customfield_deploy": {"markdown": "Deployment ready"},
            "deployment_notes": {"markdown": "Fallback"},
        }
    ]

    settings = {
        "release": {"validation_doc": {"deployment_notes_field_id": "customfield_deploy"}},
        "jira": {"base_url": "https://example.invalid"},
    }

    payload = build_validation_doc(
        issues=issues, settings=settings, base_url=settings["jira"]["base_url"]
    )

    assert payload["deployment_notes_field_id"] == "customfield_deploy"
    assert payload["items"] == [
        {
            "issue_key": "APP-1",
            "summary": "First story",
            "deployment_notes": "Deployment ready",
            "url": "https://example.invalid/browse/APP-1",
        }
    ]
