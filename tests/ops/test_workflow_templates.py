from pathlib import Path

from ruamel.yaml import YAML

WORKFLOW_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"
_yaml = YAML(typ="safe")


def _load_workflow(filename: str) -> dict:
    path = WORKFLOW_DIR / filename
    return _yaml.load(path.read_text(encoding="utf-8"))


def test_orchestrator_runner_configuration() -> None:
    workflow = _load_workflow("orchestrator-runner.yml")

    triggers = workflow.get("on", {})
    assert "workflow_dispatch" in triggers
    assert "issue_comment" in triggers

    permissions = workflow.get("permissions")
    assert permissions["workflows"] == "write"
    assert permissions["issues"] == "read"

    orchestrate_job = workflow["jobs"]["orchestrate"]
    assert orchestrate_job["uses"] == "./.github/workflows/reusable-orchestrator.yml"
    assert orchestrate_job["with"]["allowed-roles"] == "MEMBER,OWNER,TRIAGE"
    assert "allowed-users" in orchestrate_job["with"]
    assert orchestrate_job["secrets"]["orchestrator-bot-token"] == "${{ secrets.ORCHESTRATOR_BOT_TOKEN }}"


def test_reusable_orchestrator_contains_expected_steps() -> None:
    workflow = _load_workflow("reusable-orchestrator.yml")

    call = workflow["on"]["workflow_call"]
    assert call["secrets"]["orchestrator-bot-token"]["required"] is True

    job = workflow["jobs"]["dispatch"]
    assert job["env"]["TZ"] == "America/Phoenix"

    steps = job["steps"]
    assert any(step.get("uses") == "actions/github-script@v7" for step in steps)
    assert any("dispatch-log.ndjson" in (step.get("run") or "") for step in steps)
    assert any(step.get("name") == "Calculate Phoenix run identifier" for step in steps)
    assert any(step.get("uses") == "actions/upload-artifact@v4" for step in steps)
