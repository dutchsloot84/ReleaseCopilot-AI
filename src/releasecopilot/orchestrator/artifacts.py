"""Artifact writers for release note and validation exports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping, MutableMapping, Sequence
import uuid

import pandas as pd
from pandas import ExcelWriter
from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")


class ArtifactWriteError(RuntimeError):
    """Raised when release artifact persistence fails."""


@dataclass(frozen=True)
class RunMetadata:
    run_id: str
    git_sha: str
    generated_at: str
    timezone: str

    def as_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "git_sha": self.git_sha,
            "generated_at": self.generated_at,
            "timezone": self.timezone,
        }


def _resolve_git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):  # pragma: no cover - defensive
        return "unknown"
    value = result.stdout.strip()
    return value or "unknown"


def generate_run_metadata(
    *,
    run_id: str | None = None,
    git_sha: str | None = None,
    now: datetime | None = None,
    tz: ZoneInfo | None = None,
) -> RunMetadata:
    zone = tz or PHOENIX_TZ
    timestamp = (now or datetime.now(tz=zone)).astimezone(zone)
    resolved_run_id = run_id or uuid.uuid4().hex
    resolved_sha = git_sha or _resolve_git_sha()
    return RunMetadata(
        run_id=resolved_run_id,
        git_sha=resolved_sha,
        generated_at=timestamp.isoformat(timespec="seconds"),
        timezone=zone.key,
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise ArtifactWriteError(f"Failed to write JSON artifact at {path}: {exc}") from exc


def _copy_latest(source: Path, destination: Path) -> None:
    try:
        shutil.copyfile(source, destination)
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise ArtifactWriteError(f"Failed to update latest artifact at {destination}: {exc}") from exc


def _safe_sheet_name(name: str) -> str:
    trimmed = name.strip() or "Notes"
    return trimmed[:31]


def _write_excel(
    path: Path,
    *,
    metadata: RunMetadata,
    sheets: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame([metadata.as_dict()]).to_excel(writer, sheet_name="Metadata", index=False)
            for name, rows in sheets.items():
                df = pd.DataFrame(rows)
                df.to_excel(writer, sheet_name=_safe_sheet_name(name), index=False)
    except OSError as exc:  # pragma: no cover - filesystem guard
        raise ArtifactWriteError(f"Failed to write Excel artifact at {path}: {exc}") from exc


def write_release_notes_artifacts(
    *,
    grouped_notes: Mapping[str, Sequence[Mapping[str, Any]]],
    tabular_rows: Sequence[Mapping[str, Any]],
    metadata: RunMetadata,
    out_dir: Path,
) -> dict[str, Path]:
    """Persist release notes to JSON/Excel with Phoenix metadata."""

    payload: MutableMapping[str, Any] = dict(metadata.as_dict())
    payload["notes"] = {bucket: list(rows) for bucket, rows in grouped_notes.items()}
    json_path = out_dir / f"release_notes_{metadata.run_id}.json"
    _write_json(json_path, payload)
    latest_json = out_dir / "latest.json"
    _write_json(latest_json, payload)

    sheets: dict[str, Sequence[Mapping[str, Any]]] = {}
    for bucket, rows in grouped_notes.items():
        sheets[bucket] = rows
    if tabular_rows:
        sheets.setdefault("All Notes", tabular_rows)

    excel_path = out_dir / f"release_notes_{metadata.run_id}.xlsx"
    _write_excel(excel_path, metadata=metadata, sheets=sheets)
    latest_excel = out_dir / "latest.xlsx"
    _copy_latest(excel_path, latest_excel)

    return {
        "json": json_path,
        "latest_json": latest_json,
        "excel": excel_path,
        "latest_excel": latest_excel,
    }


def write_validation_artifact(
    *,
    items: Sequence[Mapping[str, Any]],
    field_id: str,
    metadata: RunMetadata,
    out_dir: Path,
) -> dict[str, Path]:
    """Persist validation documents to JSON/Excel with Phoenix metadata."""

    payload: MutableMapping[str, Any] = dict(metadata.as_dict())
    payload["deployment_notes_field_id"] = field_id
    payload["items"] = list(items)

    json_path = out_dir / f"validation_{metadata.run_id}.json"
    _write_json(json_path, payload)
    latest_json = out_dir / "latest.json"
    _write_json(latest_json, payload)

    sheets = {"Validation": items}
    excel_path = out_dir / f"validation_{metadata.run_id}.xlsx"
    _write_excel(excel_path, metadata=metadata, sheets=sheets)
    latest_excel = out_dir / "latest.xlsx"
    _copy_latest(excel_path, latest_excel)

    return {
        "json": json_path,
        "latest_json": latest_json,
        "excel": excel_path,
        "latest_excel": latest_excel,
    }


__all__ = [
    "ArtifactWriteError",
    "RunMetadata",
    "PHOENIX_TZ",
    "generate_run_metadata",
    "write_release_notes_artifacts",
    "write_validation_artifact",
]
