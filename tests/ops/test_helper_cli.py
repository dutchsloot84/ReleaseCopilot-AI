from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from scripts.github.wave2_helper import cli


def _write_temp_config(tmp_path: Path) -> Path:
    base = yaml.safe_load(Path("config/wave2_helper.yml").read_text(encoding="utf-8"))
    artifact_dirs = {}
    for key, value in base["artifact_dirs"].items():
        artifact_dirs[key] = str(tmp_path / value)
    base["artifact_dirs"] = artifact_dirs
    config_path = tmp_path / "wave2_helper.yml"
    config_path.write_text(yaml.safe_dump(base), encoding="utf-8")
    return config_path


def test_cli_pipeline_generates_artifacts(tmp_path: Path) -> None:
    config_path = _write_temp_config(tmp_path)
    runner = CliRunner()
    issues_path = Path("tests/fixtures/issues_wave2.json")

    result_collect = runner.invoke(
        cli,
        ["--config", str(config_path), "collect", "--issues-json", str(issues_path)],
    )
    assert result_collect.exit_code == 0, result_collect.output

    config_payload = yaml.safe_load(config_path.read_text())
    artifact_dirs = {
        key: Path(value) for key, value in config_payload["artifact_dirs"].items()
    }

    collected_path = artifact_dirs["collected_issues"]
    assert collected_path.exists()

    result_prioritize = runner.invoke(cli, ["--config", str(config_path), "prioritize"])
    assert result_prioritize.exit_code == 0, result_prioritize.output

    prioritized_path = artifact_dirs["prioritized"]
    payload = json.loads(prioritized_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["timezone"] == "America/Phoenix"

    result_seed = runner.invoke(cli, ["--config", str(config_path), "seed"])
    assert result_seed.exit_code == 0, result_seed.output

    prompts_dir = artifact_dirs["prompts_dir"]
    seeded = list(prompts_dir.glob("*.md"))
    assert seeded, "expected prompts to be generated"

    result_post = runner.invoke(cli, ["--config", str(config_path), "post"])
    assert result_post.exit_code == 0, result_post.output

    comments_dir = artifact_dirs["comments"]
    assert any(path.suffix == ".md" for path in comments_dir.iterdir())

    result_open_pr = runner.invoke(cli, ["--config", str(config_path), "open-pr"])
    assert result_open_pr.exit_code == 0, result_open_pr.output

    pr_template = artifact_dirs["pr_template"]
    assert pr_template.exists()

    activity_path = artifact_dirs["activity_log"]
    entries = [
        json.loads(line)
        for line in activity_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert {entry["command"] for entry in entries} >= {
        "collect",
        "prioritize",
        "seed",
        "post",
        "open-pr",
    }
    assert all(entry["timezone"] == "America/Phoenix" for entry in entries)
