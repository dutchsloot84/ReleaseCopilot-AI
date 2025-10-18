"""Archive helpers for Wave generator outputs."""

from __future__ import annotations

import io
import json
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

PHOENIX_TZ: Final[str] = "America/Phoenix"


@dataclass(frozen=True)
class ArchiveResult:
    """Result payload returned when archiving completes."""

    tarball: Path
    marker: Path


def archive_previous_wave(
    current_wave: int,
    *,
    base_dir: Path | None = None,
    timezone: str = PHOENIX_TZ,
    now: datetime | None = None,
) -> ArchiveResult | None:
    """Archive the previous wave MOP at most once per Phoenix day."""

    if current_wave <= 1:
        return None

    root = Path(base_dir) if base_dir is not None else Path.cwd()
    source = root / "docs" / "mop" / f"mop_wave{current_wave - 1}.md"
    if not source.exists():
        return None

    zone = ZoneInfo(timezone)
    moment = (now or datetime.now(tz=zone)).astimezone(zone)
    archive_dir = root / "artifacts" / "issues" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    day_stamp = moment.strftime("%Y-%m-%d")
    marker = archive_dir / f"wave{current_wave - 1}_{day_stamp}.lock"
    if marker.exists():
        return None

    tarball = archive_dir / f"wave{current_wave - 1}_{day_stamp}.tar.gz"
    metadata = {
        "archived_at": moment.isoformat(),
        "timezone": timezone,
        "source": source.as_posix(),
    }
    with tarfile.open(tarball, mode="w:gz") as handle:
        handle.add(source, arcname=source.name)
        payload = json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8")
        info = tarfile.TarInfo(name=f"wave{current_wave - 1}_metadata.json")
        info.size = len(payload)
        handle.addfile(info, io.BytesIO(payload))

    marker.write_text("archived", encoding="utf-8")
    return ArchiveResult(tarball=tarball, marker=marker)
