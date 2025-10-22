"""Unit tests for the wave generator archiver helpers."""

from __future__ import annotations

from pathlib import Path

from releasecopilot.wave import wave2_helper as generator


def _seed_mop(previous_wave_root: Path, content: str = "wave2") -> Path:
    previous_wave_root.mkdir(parents=True, exist_ok=True)
    source = previous_wave_root / "mop_wave2.md"
    source.write_text(content, encoding="utf-8")
    return source


def test_archive_is_idempotent(generator_env: Path) -> None:
    """The archiver should only copy the MOP once per Phoenix day."""

    mop_root = generator_env / "docs/mop"
    _seed_mop(mop_root)

    generator.archive_previous_wave_mop(2)
    generator.archive_previous_wave_mop(2)

    archives = sorted((mop_root / "archive").glob("*.md"))
    assert len(archives) == 1
    assert archives[0].read_text(encoding="utf-8") == "wave2"


def test_archive_filename_includes_phoenix_date(generator_env: Path) -> None:
    """Archived filenames should include the Phoenix-local date stamp."""

    mop_root = generator_env / "docs/mop"
    _seed_mop(mop_root, content="wave2-contents")

    generator.archive_previous_wave_mop(2)

    archives = list((mop_root / "archive").glob("*.md"))
    assert archives, "expected archive to be created"
    archived_name = archives[0].name
    assert archived_name.startswith("mop_wave2_")
    assert "2024-01-01" in archived_name
    assert archives[0].read_text(encoding="utf-8") == "wave2-contents"


def test_archive_ignores_missing_source(generator_env: Path) -> None:
    """If the previous wave MOP is missing, the archiver is a no-op."""

    mop_root = generator_env / "docs/mop"
    destination_dir = mop_root / "archive"

    generator.archive_previous_wave_mop(5)

    assert not list(destination_dir.glob("*.md"))
