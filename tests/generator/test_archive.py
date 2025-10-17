from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.generator.archive import PHOENIX_TZ, archive_previous_wave


def test_archive_runs_once_per_day(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "mop"
    docs.mkdir(parents=True)
    source = docs / "mop_wave2.md"
    source.write_text("wave2", encoding="utf-8")

    now = datetime(2024, 10, 15, 9, 0, tzinfo=ZoneInfo(PHOENIX_TZ))
    result = archive_previous_wave(
        3,
        base_dir=tmp_path,
        timezone=PHOENIX_TZ,
        now=now,
    )
    assert result is not None
    assert result.tarball.exists()
    assert result.marker.exists()

    second = archive_previous_wave(
        3,
        base_dir=tmp_path,
        timezone=PHOENIX_TZ,
        now=now.replace(hour=23),
    )
    assert second is None


def test_archive_handles_missing_wave(tmp_path: Path) -> None:
    assert archive_previous_wave(1, base_dir=tmp_path) is None
