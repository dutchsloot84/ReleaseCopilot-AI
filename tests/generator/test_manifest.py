"""Tests for the YAML-driven sub-prompt manifest generation."""

from __future__ import annotations

import json

from releasecopilot.wave import wave2_helper as generator


def test_manifest_contains_expected_metadata(sample_spec: dict[str, object]) -> None:
    """The manifest should advertise deterministic metadata."""

    items = generator.render_subprompts_and_issues(sample_spec)
    manifest_path = generator.write_manifest(sample_spec["wave"], items)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == generator.MANIFEST_SCHEMA_VERSION
    assert payload["timezone"] == generator.PHOENIX_TZ
    assert payload["generated_at"].endswith("-07:00")
    assert payload["git_sha"] == "GIT_SHA_HERE"
    assert payload["items"] == sorted(items, key=lambda item: item["slug"])


def test_resolve_generated_at_reuses_manifest_timestamp(sample_spec: dict[str, object]) -> None:
    """`resolve_generated_at` should reuse Phoenix timestamps from disk."""

    items = generator.render_subprompts_and_issues(sample_spec)
    manifest_path = generator.write_manifest(sample_spec["wave"], items)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored = generator.resolve_generated_at(sample_spec["wave"])
    assert restored == payload["generated_at"]


def test_manifest_is_idempotent(sample_spec: dict[str, object]) -> None:
    """Re-running the generator should not drift manifest contents."""

    first_items = generator.render_subprompts_and_issues(sample_spec)
    first_manifest = generator.write_manifest(sample_spec["wave"], first_items)
    snapshot = first_manifest.read_text(encoding="utf-8")

    second_items = generator.render_subprompts_and_issues(sample_spec)
    second_manifest = generator.write_manifest(sample_spec["wave"], second_items)

    assert first_items == second_items
    assert second_manifest.read_text(encoding="utf-8") == snapshot
