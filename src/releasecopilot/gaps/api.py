"""Phoenix-aware gap response helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
import uuid
from zoneinfo import ZoneInfo

PHOENIX_TZ = ZoneInfo("America/Phoenix")


@dataclass(slots=True)
class GapResponse:
    """Serializable response for correlation gap endpoints."""

    run_id: str
    git_sha: str
    generated_at: str
    timezone: str
    args: dict[str, Any]
    payload: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_args(args: Mapping[str, Any] | None) -> dict[str, Any]:
    if args is None:
        return {}
    if isinstance(args, Mapping):
        return {str(key): value for key, value in args.items()}
    raise TypeError("run args must be provided as a mapping")


def _normalize_payload(payload: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if payload is None:
        return []
    normalised: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, Mapping):
            normalised.append({str(key): value for key, value in item.items()})
    return normalised


def _resolve_timestamp(
    generated_at: datetime | str | None,
    tz: ZoneInfo,
) -> str:
    if generated_at is None:
        timestamp = datetime.now(tz=tz)
    elif isinstance(generated_at, datetime):
        timestamp = generated_at.astimezone(tz)
    elif isinstance(generated_at, str):
        parsed = datetime.fromisoformat(generated_at)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tz)
        timestamp = parsed.astimezone(tz)
    else:  # pragma: no cover - defensive path
        raise TypeError("generated_at must be datetime, ISO string, or None")
    return timestamp.isoformat(timespec="seconds")


def _build_gap_response(
    payload: Iterable[Mapping[str, Any]] | None,
    *,
    run_id: str | None,
    git_sha: str | None,
    args: Mapping[str, Any] | None,
    generated_at: datetime | str | None,
    tz: ZoneInfo | None,
) -> GapResponse:
    zone = tz or PHOENIX_TZ
    resolved_id = run_id or uuid.uuid4().hex
    response = GapResponse(
        run_id=resolved_id,
        git_sha=git_sha or "unknown",
        generated_at=_resolve_timestamp(generated_at, zone),
        timezone=zone.key if hasattr(zone, "key") else str(zone),
        args=_normalize_args(args),
        payload=_normalize_payload(payload),
    )
    return response


def stories_without_commits(
    data: Sequence[Mapping[str, Any]] | None,
    *,
    run_id: str | None = None,
    git_sha: str | None = None,
    args: Mapping[str, Any] | None = None,
    generated_at: datetime | str | None = None,
    tz: ZoneInfo | None = None,
) -> GapResponse:
    """Return Phoenix-aware metadata for stories that lack commits."""

    return _build_gap_response(
        data,
        run_id=run_id,
        git_sha=git_sha,
        args=args,
        generated_at=generated_at,
        tz=tz,
    )


def commits_without_story(
    data: Sequence[Mapping[str, Any]] | None,
    *,
    run_id: str | None = None,
    git_sha: str | None = None,
    args: Mapping[str, Any] | None = None,
    generated_at: datetime | str | None = None,
    tz: ZoneInfo | None = None,
) -> GapResponse:
    """Return Phoenix-aware metadata for commits that lack story links."""

    return _build_gap_response(
        data,
        run_id=run_id,
        git_sha=git_sha,
        args=args,
        generated_at=generated_at,
        tz=tz,
    )


__all__ = ["GapResponse", "commits_without_story", "stories_without_commits"]
