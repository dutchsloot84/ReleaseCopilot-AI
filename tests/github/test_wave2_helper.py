from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from releasecopilot.logging_config import get_logger
from scripts.github.wave2_helper import (
    Issue,
    Wave2Helper,
    Wave2HelperConfig,
    _gh_issue_list,
)


@pytest.fixture()
def helper(tmp_path: Path) -> Wave2Helper:
    config = Wave2HelperConfig.load(Path("config/wave2_helper.yml"))
    adjusted_dirs = {}
    for key, value in config.artifact_dirs.items():
        adjusted_dirs[key] = str(tmp_path / value)
    config.artifact_dirs = adjusted_dirs
    fixed_now = datetime(2025, 1, 15, 8, 30, tzinfo=ZoneInfo("America/Phoenix"))
    return Wave2Helper(config, now_provider=lambda: fixed_now)


@pytest.fixture()
def fixture_issues() -> list[Issue]:
    path = Path("tests/fixtures/issues_wave2.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Issue.from_raw(item) for item in data]


def test_prioritize_is_deterministic(helper: Wave2Helper, fixture_issues: list[Issue]) -> None:
    filtered = helper.filter_issues(fixture_issues)
    numbers = [issue.number for issue in filtered]
    assert 310 not in numbers  # filtered out by label guard

    prioritized_first = helper.prioritize(filtered)
    prioritized_second = helper.prioritize(filtered)
    assert [issue.number for issue in prioritized_first] == [
        issue.number for issue in prioritized_second
    ]
    assert [issue.number for issue in prioritized_first][:3] == [278, 279, 283]


def test_prioritized_artifact_contains_phoenix_timestamp(
    helper: Wave2Helper, fixture_issues: list[Issue]
) -> None:
    prioritized = helper.prioritize(helper.filter_issues(fixture_issues))
    artifact_path = helper.write_prioritized_artifact(prioritized)

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["timezone"] == "America/Phoenix"
    assert payload["metadata"]["generated_at"] == "2025-01-15T08:30:00-07:00"


def test_seeded_prompt_includes_constraints(
    helper: Wave2Helper, fixture_issues: list[Issue]
) -> None:
    prioritized = helper.prioritize(helper.filter_issues(fixture_issues))
    paths = helper.seed_prompts(prioritized[:1])
    content = paths[0].read_text(encoding="utf-8")
    assert "America/Phoenix" in content
    assert "Decision / Note / Action" in content
    assert f"issue #{prioritized[0].number}" in content


def test_artifact_path_joins_base(tmp_path: Path) -> None:
    config = Wave2HelperConfig.load(Path("config/wave2_helper.yml"))
    base_dir = tmp_path / "artifacts/helpers"
    config.artifact_dirs["base"] = str(base_dir)
    config.artifact_dirs["collected_issues"] = "issues.json"

    resolved = config.artifact_path("collected_issues")
    assert resolved == base_dir / "issues.json"


def test_collect_uses_gh_without_leaking_token(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    output = json.dumps(
        [
            {
                "number": 278,
                "title": "Helpers",
                "html_url": "https://example.invalid/issues/278",
                "labels": [{"name": "wave:wave2"}],
                "body": "sample",
            }
        ]
    )

    class DummyCompletedProcess:
        stdout = output

    monkeypatch.setenv("GITHUB_TOKEN", "supersecret-token")
    monkeypatch.setattr("subprocess.run", lambda *_, **__: DummyCompletedProcess())
    caplog.set_level("INFO")

    issues = _gh_issue_list(["wave:wave2"])
    assert issues[0].number == 278
    assert "supersecret-token" not in caplog.text

    helper_logger = get_logger("scripts.github.wave2_helper.test")
    helper_logger.info("verifying redaction", extra={"token": "supersecret-token"})
    assert caplog.records[-1].token == "***REDACTED***"
