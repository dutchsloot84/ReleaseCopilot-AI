"""Data models for orchestrator slash command planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")


@dataclass(frozen=True)
class SlashCommand:
    """A parsed representation of an orchestrator slash command."""

    raw_text: str
    command_name: str
    helper_prompt: str
    issue_number: int
    issued_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        timestamp = self.issued_at.astimezone(PHOENIX_TZ).isoformat()
        return {
            "command": self.command_name,
            "issue_number": self.issue_number,
            "helper_prompt": self.helper_prompt,
            "raw_text": self.raw_text,
            "phoenix_timestamp": timestamp,
        }


@dataclass(frozen=True)
class DispatchPlan:
    """Plan describing which workflow and prompt should be executed."""

    issue_number: int
    helper_prompt: str
    prompt_path: Path
    workflow_name: str
    planned_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        timestamp = self.planned_at.astimezone(PHOENIX_TZ).isoformat()
        return {
            "issue_number": self.issue_number,
            "helper_prompt": self.helper_prompt,
            "prompt_path": str(self.prompt_path),
            "workflow_name": self.workflow_name,
            "phoenix_timestamp": timestamp,
        }


@dataclass(frozen=True)
class DispatchEnvelope:
    """Envelope combining the slash command input and dispatch plan."""

    command: SlashCommand
    plan: DispatchPlan
    created_at: datetime

    @property
    def phoenix_timestamp(self) -> str:
        return self.created_at.astimezone(PHOENIX_TZ).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command.to_dict(),
            "plan": self.plan.to_dict(),
            "phoenix_timestamp": self.phoenix_timestamp,
        }

    @classmethod
    def from_components(
        cls,
        command: SlashCommand,
        plan: DispatchPlan,
        created_at: datetime,
    ) -> "DispatchEnvelope":
        return cls(command=command, plan=plan, created_at=created_at)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DispatchEnvelope":
        try:
            command_payload = payload["command"]
            plan_payload = payload["plan"]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise ValueError(f"Missing field in dispatch envelope: {exc}") from exc

        if not isinstance(command_payload, dict) or not isinstance(plan_payload, dict):
            raise ValueError(
                "Envelope payload must include mapping values for command and plan"
            )

        command = SlashCommand(
            raw_text=str(command_payload.get("raw_text", "")),
            command_name=str(command_payload.get("command", "")),
            helper_prompt=str(command_payload.get("helper_prompt", "")),
            issue_number=int(command_payload.get("issue_number", 0)),
            issued_at=_parse_phoenix_timestamp(
                command_payload.get("phoenix_timestamp")
            ),
        )

        plan = DispatchPlan(
            issue_number=int(plan_payload.get("issue_number", 0)),
            helper_prompt=str(plan_payload.get("helper_prompt", "")),
            prompt_path=Path(str(plan_payload.get("prompt_path", ""))),
            workflow_name=str(plan_payload.get("workflow_name", "")),
            planned_at=_parse_phoenix_timestamp(plan_payload.get("phoenix_timestamp")),
        )

        created_at = _parse_phoenix_timestamp(payload.get("phoenix_timestamp"))
        return cls(command=command, plan=plan, created_at=created_at)


def _parse_phoenix_timestamp(value: Any) -> datetime:
    if not value:
        raise ValueError("Phoenix timestamp is required for dispatch payloads")
    if isinstance(value, datetime):
        return value.astimezone(PHOENIX_TZ)
    if not isinstance(value, str):
        raise ValueError("Phoenix timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Invalid Phoenix timestamp: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PHOENIX_TZ)
    return parsed.astimezone(PHOENIX_TZ)
