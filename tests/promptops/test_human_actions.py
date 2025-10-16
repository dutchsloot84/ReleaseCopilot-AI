from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from scripts.promptops import human_actions


@pytest.fixture()
def sample_inputs(tmp_path: Path) -> dict[str, Path]:
    mop_text = """# Wave 2 – Master Orchestrator Prompt (MOP)

## Global constraints
- Least-priv IAM; **no secrets in logs**.
- Phoenix TZ: America/Phoenix; document cron/DST behavior.
- Deterministic artifacts with run metadata.

## Prioritized candidates for Wave 2
- Add Orchestrator workflow (slash-commands + dispatch) (#276)
- Helpers: backlog, prioritize, seed, post sub-prompts, open impl PRs (#278)
- Generate Human Actions checklist + Runbook (#279)
"""
    mop_path = tmp_path / "wave2_mop.md"
    mop_path.write_text(mop_text, encoding="utf-8")

    issues_payload = [
        {
            "number": 276,
            "title": "Add Orchestrator workflow (slash-commands + dispatch)",
            "url": "https://example.test/issues/276",
            "labels": ["automation", "high-priority"],
            "updatedAt": "2025-10-14T20:47:01Z",
        },
        {
            "number": 278,
            "title": "Helpers: backlog, prioritize, seed, post sub-prompts, open impl PRs",
            "url": "https://example.test/issues/278",
            "labels": ["automation", "cli", "high-priority"],
            "updatedAt": "2025-10-14T21:01:58Z",
        },
        {
            "number": 279,
            "title": "Generate Human Actions checklist + Runbook",
            "url": "https://example.test/issues/279",
            "labels": ["documentation", "high-priority"],
            "updatedAt": "2025-10-14T21:02:02Z",
        },
    ]
    issues_path = tmp_path / "top_issues.json"
    issues_path.write_text(json.dumps(issues_payload, indent=2), encoding="utf-8")

    output_dir = tmp_path / "artifacts"
    return {
        "mop_path": mop_path,
        "issues_path": issues_path,
        "output_dir": output_dir,
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def test_generate_human_actions_matches_golden(sample_inputs: dict[str, Path]) -> None:
    output_dir = sample_inputs["output_dir"]
    args = [
        f"--mop-path={sample_inputs['mop_path']}",
        f"--issues-path={sample_inputs['issues_path']}",
        f"--output-dir={output_dir}",
        "--author=Unit Test Harness",
        "--timestamp=2025-10-15T09:00:00-07:00",
        "--git-sha=abc123def4567890",
    ]

    metadata = human_actions.generate_human_actions(args)

    golden_dir = Path("tests/golden/human-actions")

    checklist_path = output_dir / "checklist.md"
    calendar_path = output_dir / "calendar.json"
    log_path = output_dir / "activity.ndjson"

    assert read_text(checklist_path) == read_text(golden_dir / "checklist.md")
    assert json.loads(calendar_path.read_text(encoding="utf-8")) == json.loads(
        (golden_dir / "calendar.json").read_text(encoding="utf-8")
    )
    assert read_text(log_path) == read_text(golden_dir / "activity.ndjson")

    phoenix_stamp = metadata.to_json()["phoenix_timestamp"]
    assert "America/Phoenix" in phoenix_stamp
    assert "UTC-7" in phoenix_stamp


def test_generate_human_actions_with_empty_issues(tmp_path: Path) -> None:
    mop_path = tmp_path / "wave2_mop.md"
    mop_path.write_text(
        """# Wave 2\n\n## Global constraints\n- Deterministic artifacts\n\n## Prioritized candidates for Wave 2\n- Placeholder (#999)\n""",
        encoding="utf-8",
    )
    issues_path = tmp_path / "issues.json"
    issues_path.write_text("[]", encoding="utf-8")
    output_dir = tmp_path / "out"

    metadata = human_actions.generate_human_actions(
        [
            f"--mop-path={mop_path}",
            f"--issues-path={issues_path}",
            f"--output-dir={output_dir}",
            "--author=Unit Test Harness",
            "--timestamp=2025-10-15T09:00:00-07:00",
            "--git-sha=abc123def4567890",
        ]
    )

    checklist_text = (output_dir / "checklist.md").read_text(encoding="utf-8")
    assert "No prioritized issues supplied" in checklist_text

    calendar_payload = json.loads(
        (output_dir / "calendar.json").read_text(encoding="utf-8")
    )
    assert "stub" in calendar_payload["ical"]
    assert metadata.run_hash in calendar_payload["ical"]


def test_missing_mop_path(tmp_path: Path) -> None:
    issues_path = tmp_path / "issues.json"
    issues_path.write_text("[]", encoding="utf-8")
    output_dir = tmp_path / "out"

    with pytest.raises(FileNotFoundError):
        human_actions.generate_human_actions(
            [
                f"--mop-path={tmp_path / 'missing.md'}",
                f"--issues-path={issues_path}",
                f"--output-dir={output_dir}",
                "--timestamp=2025-10-15T09:00:00-07:00",
            ]
        )


def test_format_phoenix_timestamp_handles_naive_input() -> None:
    naive = datetime(2025, 10, 15, 9, 0, 0)
    with pytest.raises(ValueError):
        # Ensure naive datetimes are not silently accepted in formatting helper.
        human_actions.format_phoenix_timestamp(naive)  # type: ignore[arg-type]
