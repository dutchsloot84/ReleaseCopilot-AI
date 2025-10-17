from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

try:
    from scripts.github import wave2_helper as generator
except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
    if exc.name == "jinja2":
        pytest.skip("jinja2 is required for generator tests", allow_module_level=True)
    raise


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
