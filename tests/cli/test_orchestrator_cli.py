from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from cli.orchestrator import register_orchestrator_parser, run_orchestrator_command

from config.loader import Defaults


@pytest.fixture()
def defaults(tmp_path: Path) -> Defaults:
    project_root = tmp_path
    (project_root / "project" / "prompts" / "wave2").mkdir(parents=True)
    return Defaults(
        project_root=project_root,
        cache_dir=project_root / "cache",
        artifact_dir=project_root / "artifacts",
        reports_dir=project_root / "reports",
        settings_path=project_root / "config.yml",
        export_formats=("json",),
    )


def _build_parser(defaults: Defaults) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rc")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_orchestrator_parser(subparsers, defaults)
    return parser


def test_plan_creates_artifact(
    tmp_path: Path, defaults: Defaults, capsys: pytest.CaptureFixture[str]
):
    prompt_path = defaults.project_root / "project" / "prompts" / "wave2" / "helper_prompt.md"
    prompt_path.write_text("helper instructions", encoding="utf-8")
    event_path = tmp_path / "event.json"
    event_path.write_text(
        Path("tests/fixtures/github_issue_comment_wave2.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    parser = _build_parser(defaults)
    args = parser.parse_args(["orchestrator", "plan", "--event-path", str(event_path)])
    exit_code = run_orchestrator_command(args, defaults)

    assert exit_code == 0
    captured = capsys.readouterr().out
    output = json.loads(captured)
    artifact_path = Path(output["artifact_path"])
    assert artifact_path.name == "plan.json"
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["plan"]["workflow_name"] == "orchestrator-runner"
    assert payload["command"]["helper_prompt"] == "helper_prompt"


def test_plan_requires_helper_token(defaults: Defaults, capsys: pytest.CaptureFixture[str]):
    event = {
        "issue": {"number": 280, "labels": [{"name": "wave:wave2"}]},
        "comment": {"body": "/orchestrate"},
    }
    parser = _build_parser(defaults)
    args = parser.parse_args(["orchestrator", "plan"])
    exit_code = run_orchestrator_command(args, defaults, stdin=[json.dumps(event)])
    assert exit_code == 1
    captured = capsys.readouterr().err
    assert "Helper prompt not provided" in captured


def test_dispatch_round_trip(
    tmp_path: Path, defaults: Defaults, capsys: pytest.CaptureFixture[str]
):
    prompt_path = defaults.project_root / "project" / "prompts" / "wave2" / "helper_prompt.md"
    prompt_path.write_text("helper instructions", encoding="utf-8")
    event_path = tmp_path / "event.json"
    event = json.loads(
        Path("tests/fixtures/github_issue_comment_wave2.json").read_text(encoding="utf-8")
    )
    event_path.write_text(json.dumps(event), encoding="utf-8")

    parser = _build_parser(defaults)
    plan_args = parser.parse_args(["orchestrator", "plan", "--event-path", str(event_path)])
    assert run_orchestrator_command(plan_args, defaults) == 0
    plan_output = json.loads(capsys.readouterr().out)
    plan_path = plan_output["artifact_path"]

    dispatch_args = parser.parse_args(["orchestrator", "dispatch", "--plan-path", plan_path])
    assert run_orchestrator_command(dispatch_args, defaults) == 0
    dispatch_payload = json.loads(capsys.readouterr().out)
    assert dispatch_payload["plan"]["workflow_name"] == "orchestrator-runner"
    assert dispatch_payload["command"]["issue_number"] == 276
