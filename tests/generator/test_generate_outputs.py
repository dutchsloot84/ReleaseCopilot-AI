from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest
from tools.generator.generator import (
    PHOENIX_TZ,
    generate_from_yaml,
    load_spec,
    render_mop_from_spec,
    render_subprompts_and_issues,
    resolve_generated_at,
    write_manifest,
)


@pytest.fixture()
def generator_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "templates").mkdir(parents=True)
    (tmp_path / "docs" / "mop").mkdir(parents=True)
    (tmp_path / "docs" / "sub-prompts").mkdir(parents=True)
    (tmp_path / "artifacts" / "issues").mkdir(parents=True)
    (tmp_path / "artifacts" / "manifests").mkdir(parents=True)
    template_root = Path(__file__).resolve().parents[2] / "templates"
    for template in template_root.iterdir():
        shutil.copy(template, tmp_path / "templates" / template.name)
    spec = tmp_path / "backlog" / "wave3.yaml"
    spec.parent.mkdir(parents=True)
    spec.write_text(
        """
wave: 99
purpose: Validate generator fixture
constraints:
  - Deterministic timestamps
quality_bar:
  - pytest
sequenced_prs:
  - title: Sample PR
    acceptance:
      - First check
    notes:
      - Remember Phoenix
      - Check docs
    labels:
      - wave:wave99
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_render_helpers_share_timestamp(generator_env: Path) -> None:
    spec = load_spec(generator_env / "backlog" / "wave3.yaml")
    timestamp = resolve_generated_at(spec["wave"], base_dir=generator_env)
    mop = render_mop_from_spec(spec, generated_at=timestamp, base_dir=generator_env)
    items = render_subprompts_and_issues(
        spec,
        generated_at=timestamp,
        base_dir=generator_env,
    )
    manifest = generator_env / "artifacts" / "manifests" / "wave99_subprompts.json"
    write_manifest(
        spec["wave"],
        items,
        generated_at=timestamp,
        base_dir=generator_env,
    )
    assert mop.exists()
    assert items
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["generated_at"] == timestamp
    assert payload["timezone"] == PHOENIX_TZ


def test_generate_from_yaml_creates_manifest(generator_env: Path) -> None:
    result = generate_from_yaml(
        "backlog/wave3.yaml",
        base_dir=generator_env,
        timezone=PHOENIX_TZ,
        archive_previous=False,
    )
    assert result.mop_path.exists()
    assert result.manifest_path.exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["items"]
    assert manifest["timezone"] == PHOENIX_TZ
