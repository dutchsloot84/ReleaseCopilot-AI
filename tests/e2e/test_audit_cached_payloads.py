from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from config.loader import load_defaults
from src.cli import app
from tests.helpers.schema_validation import assert_excel_columns, assert_json_schema

CACHED_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "cached"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "schemas" / "audit_results.schema.json"
)


@pytest.fixture()
def _defaults_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    project_root = tmp_path
    cache_dir = project_root / "cache"
    artifact_dir = project_root / "artifacts"
    reports_dir = project_root / "reports"
    (project_root / "config").mkdir()
    settings_file = project_root / "config" / "defaults.yml"
    settings_file.write_text("{}", encoding="utf-8")

    env = {
        "RC_ROOT": str(project_root),
        "RC_CACHE_DIR": str(cache_dir),
        "RC_ARTIFACT_DIR": str(artifact_dir),
        "RC_REPORTS_DIR": str(reports_dir),
        "RC_SETTINGS_FILE": str(settings_file),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(project_root)
    defaults = load_defaults(env)
    return defaults, cache_dir, artifact_dir


def _seed_cached_payloads(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("stories.json", "commits.json", "links.json", "summary.json"):
        shutil.copy2(CACHED_FIXTURES / filename, cache_dir / filename)


def test_audit_cli_uses_cached_payloads(_defaults_env: tuple) -> None:
    defaults, cache_dir, artifact_dir = _defaults_env
    _seed_cached_payloads(cache_dir)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("RC_CACHED_PAYLOAD_DIR", str(cache_dir))

    json_path = artifact_dir / "audit_results.json"
    excel_path = artifact_dir / "audit_results.xlsx"
    summary_path = artifact_dir / "audit-summary.json"

    args = [
        "audit",
        "--cache-dir",
        str(cache_dir),
        "--json",
        str(json_path),
        "--xlsx",
        str(excel_path),
        "--summary",
        str(summary_path),
        "--scope",
        "fixVersion=Wave-3",
        "--log-level",
        "ERROR",
    ]

    exit_code = app.main(args, defaults=defaults)

    monkeypatch.undo()

    assert exit_code == 0
    assert json_path.exists()
    assert excel_path.exists()
    assert summary_path.exists()

    assert_json_schema(json_path, SCHEMA_PATH)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["summary"]["timezone"] == "America/Phoenix"
    assert payload["summary"]["generated_at"].endswith("-07:00")

    assert_excel_columns(
        excel_path,
        "Audit Summary",
        [
            "total_stories",
            "total_commits",
            "stories_with_commits",
            "stories_without_commits",
            "orphan_commits",
            "generated_at",
            "timezone",
        ],
    )
    assert "America/Phoenix" in summary_path.read_text(encoding="utf-8")
