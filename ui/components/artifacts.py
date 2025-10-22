"""Reusable widgets for rendering release artifact download controls."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_ARTIFACT_TYPES = (
    ("Release Notes", "release_notes"),
    ("Validation Document", "validation"),
)

_JSON_MIME = "application/json"
_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _discover_latest(directory: Path, suffix: str) -> Path | None:
    if not directory.exists() or not directory.is_dir():
        return None
    latest = directory / f"latest{suffix}"
    if latest.exists():
        return latest
    candidates = sorted(
        directory.glob(f"*{suffix}"), key=lambda file: file.stat().st_mtime, reverse=True
    )
    return candidates[0] if candidates else None


def _render_download(label: str, path: Path, *, mime: str) -> None:
    try:
        payload = path.read_bytes()
    except OSError:  # pragma: no cover - UI feedback path
        st.warning(f"Unable to read artifact at {path}")
        return
    st.download_button(label, data=payload, file_name=path.name, mime=mime)


def render_release_artifacts_panel(*, base_dir: Path | str) -> None:
    """Render download buttons for release notes and validation artifacts."""

    base_path = Path(base_dir)
    st.markdown("### Release Artifacts")

    availability: list[tuple[str, Path | None, Path | None]] = []
    for label, folder in _ARTIFACT_TYPES:
        artifact_dir = base_path / folder
        availability.append(
            (
                label,
                _discover_latest(artifact_dir, ".json"),
                _discover_latest(artifact_dir, ".xlsx"),
            )
        )

    if not any(json_path or excel_path for _, json_path, excel_path in availability):
        st.caption("Release artifacts are unavailable. Generate exports to enable downloads.")
        return

    for label, json_path, excel_path in availability:
        if not json_path and not excel_path:
            st.caption(f"{label}: no artifacts generated yet.")
            continue
        st.markdown(f"#### {label}")
        if json_path:
            _render_download(f"Download {label.lower()} (JSON)", json_path, mime=_JSON_MIME)
        if excel_path:
            _render_download(f"Download {label.lower()} (Excel)", excel_path, mime=_EXCEL_MIME)


__all__ = ["render_release_artifacts_panel"]
