"""Orchestrator CLI entry points for planning and dispatching helper workflows."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from config.loader import Defaults
from releasecopilot.logging_config import get_logger
from releasecopilot.orchestrator.command import (
    DispatchEnvelope,
    DispatchPlan,
    SlashCommand,
)

LOGGER = get_logger(__name__)
PHOENIX_TZ = ZoneInfo("America/Phoenix")


class OrchestratorCommandError(RuntimeError):
    """Raised when orchestrator commands fail validation."""


@dataclass(frozen=True)
class OrchestratorContext:
    defaults: Defaults
    now: datetime

    @property
    def phoenix_timestamp(self) -> str:
        return self.now.astimezone(PHOENIX_TZ).isoformat()


def register_orchestrator_parser(
    subparsers: argparse._SubParsersAction, defaults: Defaults
) -> None:
    orchestrator = subparsers.add_parser(
        "orchestrator",
        help="Plan and dispatch helper workflows for wave 2 prompts",
    )
    orchestrator_sub = orchestrator.add_subparsers(dest="subcommand", required=True)

    plan = orchestrator_sub.add_parser(
        "plan",
        help="Compute the dispatch plan for an orchestrator slash command",
    )
    plan.add_argument(
        "--event-path",
        help="Path to the GitHub issue_comment payload; defaults to stdin",
    )
    plan.add_argument(
        "--artifact-root",
        default=str(defaults.project_root / "artifacts" / "orchestrator"),
        help="Directory where plan artifacts should be written",
    )

    dispatch = orchestrator_sub.add_parser(
        "dispatch",
        help="Emit the dispatch envelope for an existing orchestrator plan",
    )
    dispatch.add_argument(
        "--plan-path",
        required=True,
        help="Path to a plan.json artifact produced by 'rc orchestrator plan'",
    )


def run_orchestrator_command(
    args: argparse.Namespace, defaults: Defaults, *, stdin: Iterable[str] | None = None
) -> int:
    """Execute the orchestrator CLI command based on parsed arguments."""

    subcommand = getattr(args, "subcommand", None)
    context = OrchestratorContext(defaults=defaults, now=datetime.now(tz=PHOENIX_TZ))
    if subcommand == "plan":
        try:
            envelope, artifact_path = _handle_plan(args, context, stdin=stdin)
        except OrchestratorCommandError as exc:
            LOGGER.error(
                "Orchestrator plan failed",
                extra={
                    "command": "plan",
                    "phoenix_timestamp": context.phoenix_timestamp,
                    "error": str(exc),
                },
            )
            print(str(exc), file=sys.stderr)
            return 1

        LOGGER.info(
            "Planned orchestrator dispatch",
            extra={
                "command": "plan",
                "issue_number": envelope.plan.issue_number,
                "phoenix_timestamp": context.phoenix_timestamp,
            },
        )
        output = {
            "artifact_path": str(artifact_path),
            "workflow": envelope.plan.workflow_name,
        }
        print(json.dumps(output, indent=2))
        return 0

    if subcommand == "dispatch":
        try:
            envelope = _handle_dispatch(args, context)
        except OrchestratorCommandError as exc:
            LOGGER.error(
                "Orchestrator dispatch failed",
                extra={
                    "command": "dispatch",
                    "phoenix_timestamp": context.phoenix_timestamp,
                    "error": str(exc),
                },
            )
            print(str(exc), file=sys.stderr)
            return 1

        LOGGER.info(
            "Dispatch envelope ready",
            extra={
                "command": "dispatch",
                "issue_number": envelope.plan.issue_number,
                "phoenix_timestamp": context.phoenix_timestamp,
            },
        )
        print(json.dumps(envelope.to_dict(), indent=2))
        return 0

    raise OrchestratorCommandError(f"Unsupported subcommand: {subcommand}")


def _handle_plan(
    args: argparse.Namespace,
    context: OrchestratorContext,
    *,
    stdin: Iterable[str] | None = None,
) -> tuple[DispatchEnvelope, Path]:
    event_payload = _load_event_payload(args, stdin=stdin)
    slash_command = _parse_slash_command(event_payload, context=context)
    plan = _build_dispatch_plan(slash_command, context=context)
    envelope = DispatchEnvelope.from_components(slash_command, plan, context.now)
    artifact_path = _write_plan_artifact(envelope, args, context)
    return envelope, artifact_path


def _handle_dispatch(args: argparse.Namespace, context: OrchestratorContext) -> DispatchEnvelope:
    plan_path = Path(args.plan_path)
    if not plan_path.exists():
        raise OrchestratorCommandError(f"Dispatch plan not found at {plan_path}")
    try:
        payload = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OrchestratorCommandError(f"Plan file {plan_path} is not valid JSON: {exc}") from exc

    try:
        envelope = DispatchEnvelope.from_dict(payload)
    except ValueError as exc:
        raise OrchestratorCommandError(str(exc)) from exc
    return envelope


def _load_event_payload(
    args: argparse.Namespace,
    *,
    stdin: Iterable[str] | None = None,
) -> dict[str, Any]:
    if args.event_path:
        path = Path(args.event_path)
        if not path.exists():
            raise OrchestratorCommandError(f"Event payload not found at {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise OrchestratorCommandError(f"Event file {path} is not valid JSON: {exc}") from exc

    if stdin is None:
        stdin = sys.stdin
    content = "".join(stdin)
    if not content.strip():
        raise OrchestratorCommandError("No event payload provided via stdin")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OrchestratorCommandError(f"Stdin payload is not valid JSON: {exc}") from exc


def _parse_slash_command(
    event_payload: dict[str, Any],
    *,
    context: OrchestratorContext,
) -> SlashCommand:
    issue = event_payload.get("issue")
    if not isinstance(issue, dict):
        raise OrchestratorCommandError("Event payload is missing issue information")
    issue_number = issue.get("number")
    if not isinstance(issue_number, int):
        raise OrchestratorCommandError("Issue payload did not include a numeric issue number")

    labels = issue.get("labels", [])
    label_names = [label.get("name") for label in labels if isinstance(label, dict)]
    if "wave:wave2" not in label_names:
        raise OrchestratorCommandError("Issue does not include required label 'wave:wave2'")

    comment = event_payload.get("comment")
    if not isinstance(comment, dict):
        raise OrchestratorCommandError("Event payload is missing comment information")
    body = comment.get("body")
    if not isinstance(body, str):
        raise OrchestratorCommandError("Comment body is not a string")

    helper_prompt = _extract_helper_prompt(body)
    timestamp = context.now

    return SlashCommand(
        raw_text=body,
        command_name="orchestrate",
        helper_prompt=helper_prompt,
        issue_number=issue_number,
        issued_at=timestamp,
    )


def _extract_helper_prompt(body: str) -> str:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    command_line = next((line for line in lines if line.startswith("/orchestrate")), None)
    if not command_line:
        raise OrchestratorCommandError("No /orchestrate command found in comment")

    tokens = command_line.split()
    if tokens[0] != "/orchestrate":
        raise OrchestratorCommandError("Invalid slash command prefix")

    helper_value = None
    for token in tokens[1:]:
        if token.startswith("helper:"):
            helper_value = token.split(":", 1)[1].strip()
            break
        if token.startswith("helper="):
            helper_value = token.split("=", 1)[1].strip()
            break
        if helper_value is None:
            helper_value = token.strip()
            break

    if not helper_value:
        raise OrchestratorCommandError("Helper prompt not provided in /orchestrate command")
    return helper_value


def _build_dispatch_plan(
    slash_command: SlashCommand,
    *,
    context: OrchestratorContext,
) -> DispatchPlan:
    prompts_root = context.defaults.project_root / "project" / "prompts" / "wave2"
    helper_name = slash_command.helper_prompt
    candidate = prompts_root / helper_name
    if candidate.is_dir():
        raise OrchestratorCommandError(f"Helper prompt refers to a directory: {helper_name}")
    if candidate.suffix:
        prompt_path = candidate
    else:
        prompt_path = candidate.with_suffix(".md")

    if not prompt_path.exists():
        raise OrchestratorCommandError(f"Helper prompt file not found: {prompt_path.name}")

    workflow_name = "orchestrator-runner"
    return DispatchPlan(
        issue_number=slash_command.issue_number,
        helper_prompt=slash_command.helper_prompt,
        prompt_path=prompt_path,
        workflow_name=workflow_name,
        planned_at=context.now,
    )


def _write_plan_artifact(
    envelope: DispatchEnvelope,
    args: argparse.Namespace,
    context: OrchestratorContext,
) -> Path:
    artifact_root = Path(args.artifact_root)
    timestamp = envelope.phoenix_timestamp
    target_dir = artifact_root / timestamp
    target_dir.mkdir(parents=True, exist_ok=True)
    plan_path = target_dir / "plan.json"
    payload = envelope.to_dict()
    plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return plan_path
