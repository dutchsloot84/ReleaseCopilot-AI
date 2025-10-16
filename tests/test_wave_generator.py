from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from scripts.github import wave2_helper as generator

FIXED_NOW = datetime(2024, 1, 1, 12, 0, tzinfo=ZoneInfo(generator.PHOENIX_TZ))


def _copy_templates(dst: Path) -> None:
    template_root = Path(__file__).resolve().parents[1] / "templates"
    for template in ("mop.md.j2", "subprompt.md.j2", "issue_body.md.j2"):
        shutil.copyfile(template_root / template, dst / template)


@pytest.fixture()
def generator_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "templates").mkdir(parents=True)
    (tmp_path / "backlog").mkdir(parents=True)
    (tmp_path / "docs/mop/archive").mkdir(parents=True)
    (tmp_path / "docs/sub-prompts").mkdir(parents=True)
    (tmp_path / "artifacts/issues").mkdir(parents=True)
    (tmp_path / "artifacts/manifests").mkdir(parents=True)
    _copy_templates(tmp_path / "templates")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(generator, "phoenix_now", lambda: FIXED_NOW)
    return tmp_path


@pytest.fixture()
def sample_spec(generator_env: Path) -> dict:
    spec_path = generator_env / "backlog/sample.yaml"
    spec_path.write_text(
        """
wave: 3
purpose: Ensure sample wave for testing
constraints:
  - Respect America/Phoenix scheduling
quality_bar:
  - Maintain ≥70% coverage on generators
sequenced_prs:
  - title: Sample PR
    acceptance:
      - Render mop
      - Render prompts
    notes:
      - Include Phoenix reminder
    labels:
      - wave:wave3
      - testing
""".strip(),
        encoding="utf-8",
    )
    return generator.load_spec(spec_path)


def test_archive_once_per_day(generator_env: Path) -> None:
    mop_root = generator_env / "docs/mop"
    mop_root.mkdir(exist_ok=True)
    (mop_root / "mop_wave2.md").write_text("wave2", encoding="utf-8")
    generator.archive_previous_wave_mop(2)
    generator.archive_previous_wave_mop(2)
    archives = list((mop_root / "archive").glob("*.md"))
    assert len(archives) == 1
    assert archives[0].read_text(encoding="utf-8") == "wave2"


def test_mop_render_minimal_spec(sample_spec: dict) -> None:
    mop_path = generator.render_mop_from_yaml(sample_spec)
    content = mop_path.read_text(encoding="utf-8")
    assert "Wave 3 Mission Outline Plan" in content
    assert "America/Phoenix" in content
    assert "Sample PR" in content


def test_subprompts_render(sample_spec: dict) -> None:
    items = generator.render_subprompts_and_issues(sample_spec)
    assert len(items) == len(sample_spec["sequenced_prs"])
    subprompt_path = Path(items[0]["subprompt_path"])
    assert subprompt_path.read_text(encoding="utf-8").startswith(
        "# Wave 3 – Sub-Prompt"
    )


def test_manifest_schema(sample_spec: dict) -> None:
    items = generator.render_subprompts_and_issues(sample_spec)
    manifest_path = generator.write_manifest(sample_spec["wave"], items)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == generator.MANIFEST_SCHEMA_VERSION
    assert payload["timezone"] == generator.PHOENIX_TZ
    assert len(payload["items"]) == len(sample_spec["sequenced_prs"])


def test_idempotent_outputs(sample_spec: dict) -> None:
    first_items = generator.render_subprompts_and_issues(sample_spec)
    first_manifest = generator.write_manifest(sample_spec["wave"], first_items)
    first_hashes = {
        "mop": hashlib.sha256(
            generator.render_mop_from_yaml(sample_spec).read_bytes()
        ).hexdigest(),
        "subprompt": hashlib.sha256(
            Path(first_items[0]["subprompt_path"]).read_bytes()
        ).hexdigest(),
        "manifest": hashlib.sha256(first_manifest.read_bytes()).hexdigest(),
    }
    second_items = generator.render_subprompts_and_issues(sample_spec)
    second_manifest = generator.write_manifest(sample_spec["wave"], second_items)
    assert first_items == second_items
    assert (
        hashlib.sha256(
            generator.render_mop_from_yaml(sample_spec).read_bytes()
        ).hexdigest()
        == first_hashes["mop"]
    )
    assert (
        hashlib.sha256(Path(second_items[0]["subprompt_path"]).read_bytes()).hexdigest()
        == first_hashes["subprompt"]
    )
    assert (
        hashlib.sha256(second_manifest.read_bytes()).hexdigest()
        == first_hashes["manifest"]
    )
