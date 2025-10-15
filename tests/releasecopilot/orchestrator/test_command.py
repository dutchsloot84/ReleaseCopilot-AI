from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from releasecopilot.orchestrator.command import DispatchEnvelope, DispatchPlan, SlashCommand


def test_serialization_uses_phoenix_timezone(tmp_path: Path) -> None:
    issued_at = datetime(2024, 1, 1, 19, 0, tzinfo=timezone.utc)
    planned_at = datetime(2024, 1, 1, 19, 5, tzinfo=timezone.utc)
    command = SlashCommand(
        raw_text="/orchestrate helper:helper_prompt",
        command_name="orchestrate",
        helper_prompt="helper_prompt",
        issue_number=276,
        issued_at=issued_at,
    )
    plan = DispatchPlan(
        issue_number=276,
        helper_prompt="helper_prompt",
        prompt_path=tmp_path / "helper_prompt.md",
        workflow_name="orchestrator-runner",
        planned_at=planned_at,
    )
    envelope = DispatchEnvelope.from_components(command, plan, planned_at)

    payload = envelope.to_dict()
    assert list(payload.keys()) == ["command", "plan", "phoenix_timestamp"]
    assert payload["command"]["phoenix_timestamp"].endswith("-07:00")
    assert payload["plan"]["phoenix_timestamp"].endswith("-07:00")
    assert payload["plan"]["prompt_path"].endswith("helper_prompt.md")


def test_from_dict_roundtrip(tmp_path: Path) -> None:
    issued_at = datetime(2024, 1, 2, 18, 0, tzinfo=timezone.utc)
    plan_at = datetime(2024, 1, 2, 18, 10, tzinfo=timezone.utc)
    command = SlashCommand(
        raw_text="/orchestrate helper:helper_prompt",
        command_name="orchestrate",
        helper_prompt="helper_prompt",
        issue_number=300,
        issued_at=issued_at,
    )
    plan = DispatchPlan(
        issue_number=300,
        helper_prompt="helper_prompt",
        prompt_path=tmp_path / "helper_prompt.md",
        workflow_name="orchestrator-runner",
        planned_at=plan_at,
    )
    original = DispatchEnvelope.from_components(command, plan, plan_at)
    payload = original.to_dict()

    restored = DispatchEnvelope.from_dict(payload)
    assert restored.plan.workflow_name == "orchestrator-runner"
    assert restored.command.issue_number == 300
    assert restored.phoenix_timestamp == payload["phoenix_timestamp"]


def test_from_dict_requires_timestamp() -> None:
    payload = {
        "command": {
            "command": "orchestrate",
            "helper_prompt": "helper_prompt",
            "issue_number": 1,
            "raw_text": "/orchestrate helper:helper_prompt",
            "phoenix_timestamp": "2024-01-01T12:00:00-07:00",
        },
        "plan": {
            "issue_number": 1,
            "helper_prompt": "helper_prompt",
            "prompt_path": "helper_prompt.md",
            "workflow_name": "orchestrator-runner",
            "phoenix_timestamp": "2024-01-01T12:05:00-07:00",
        },
    }
    with pytest.raises(ValueError):
        DispatchEnvelope.from_dict(payload)
