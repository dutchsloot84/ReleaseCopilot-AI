"""Core Wave generator orchestration utilities."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Callable, Final, Iterable, Mapping
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader
from slugify import slugify
import yaml

from .archive import PHOENIX_TZ as ARCHIVE_TZ, ArchiveResult, archive_previous_wave

PHOENIX_TZ: Final[str] = ARCHIVE_TZ


@dataclass(frozen=True)
class GeneratorResult:
    """Structured result describing generated artifacts."""

    mop_path: Path
    manifest_path: Path
    items: list[dict[str, Any]]
    generated_at: str
    archive: ArchiveResult | None


@dataclass(frozen=True)
class TimezoneLabel:
    """Presentation helpers for timezone rendering."""

    summary: str
    context: str
    parenthetical: str


def zoned_now(timezone: str = PHOENIX_TZ) -> datetime:
    """Return current time in the requested timezone (default Phoenix)."""

    zone = ZoneInfo(timezone)
    return datetime.now(tz=zone).replace(microsecond=0)


def format_timezone_label(timezone: str) -> TimezoneLabel:
    """Return human-readable timezone label for templates."""

    if timezone == PHOENIX_TZ:
        summary = "America/Phoenix · no DST"
        context = "America/Phoenix (no DST)"
    else:
        summary = context = timezone
    return TimezoneLabel(
        summary=summary,
        context=context,
        parenthetical=f"({summary})",
    )


def _jinja_environment(templates_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return path
    path.write_text(content, encoding="utf-8")
    return path


def _stringify_list(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for entry in values or []:
        if entry is None:
            continue
        if isinstance(entry, Mapping):
            rendered = ", ".join(f"{key}: {value}" for key, value in entry.items())
            result.append(rendered)
        else:
            result.append(str(entry))
    return result


def _normalize_guidance(payload: Any) -> dict[str, str]:
    guidance: dict[str, str] = {}
    if not isinstance(payload, Mapping):
        return guidance
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, list):
            text = "\n".join(str(item) for item in value if item is not None)
        else:
            text = str(value)
        guidance[str(key)] = text
    return guidance


def load_spec(spec_path: Path | str) -> dict[str, Any]:
    """Load a Wave specification from YAML."""

    path = Path(spec_path)
    with path.open("r", encoding="utf-8") as handle:
        raw_spec = yaml.safe_load(handle) or {}

    if "wave" not in raw_spec:
        raise ValueError("Missing required 'wave' field in spec")

    wave = int(raw_spec["wave"])
    sequenced: list[dict[str, Any]] = []
    for entry in raw_spec.get("sequenced_prs", []) or []:
        sequenced.append(
            {
                "id": str(entry.get("id")) if entry.get("id") is not None else None,
                "title": str(entry.get("title", "")).strip(),
                "acceptance": _stringify_list(entry.get("acceptance") or []),
                "notes": _stringify_list(entry.get("notes") or []),
                "labels": _stringify_list(entry.get("labels") or []),
                "guidance": _normalize_guidance(entry.get("guidance")),
            }
        )

    return {
        "wave": wave,
        "purpose": str(raw_spec.get("purpose", "")).strip(),
        "constraints": _stringify_list(raw_spec.get("constraints") or []),
        "quality_bar": _stringify_list(raw_spec.get("quality_bar") or []),
        "sequenced_prs": sequenced,
    }


def resolve_generated_at(
    wave: int,
    *,
    base_dir: Path | None = None,
    fallback: datetime | None = None,
) -> str:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    manifest_path = root / "artifacts" / "manifests" / f"wave{wave}_subprompts.json"
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        existing = payload.get("generated_at")
        if isinstance(existing, str) and existing.strip():
            return existing
    moment = fallback or zoned_now()
    return moment.isoformat()


def render_mop_from_spec(
    spec: Mapping[str, Any],
    *,
    generated_at: str,
    base_dir: Path | None = None,
    timezone_label: TimezoneLabel | None = None,
) -> Path:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    templates_dir = root / "templates"
    env = _jinja_environment(templates_dir)
    template = env.get_template("mop.md.j2")
    content = template.render(
        wave=spec["wave"],
        purpose=spec.get("purpose", ""),
        constraints=spec.get("constraints", []),
        quality_bar=spec.get("quality_bar", []),
        sequenced_prs=spec.get("sequenced_prs", []),
        generated_at=generated_at,
        timezone_parenthetical=(
            (timezone_label or format_timezone_label(PHOENIX_TZ)).parenthetical
        ),
    )
    path = root / "docs" / "mop" / f"mop_wave{spec['wave']}.md"
    return _write_text(path, content)


def render_subprompts_and_issues(
    spec: Mapping[str, Any],
    *,
    generated_at: str,
    base_dir: Path | None = None,
    timezone_label: TimezoneLabel | None = None,
) -> list[dict[str, Any]]:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    templates_dir = root / "templates"
    env = _jinja_environment(templates_dir)
    sub_template = env.get_template("subprompt.md.j2")
    issue_template = env.get_template("issue_body.md.j2")
    wave = spec["wave"]
    label = timezone_label or format_timezone_label(PHOENIX_TZ)
    subprompt_root = root / "docs" / "sub-prompts" / f"wave{wave}"
    issue_root = root / "artifacts" / "issues" / f"wave{wave}"
    items: list[dict[str, Any]] = []
    for pr in spec.get("sequenced_prs", []):
        title = pr.get("title", "")
        slug = slugify(title) or f"wave{wave}-item"
        normalized = {
            "id": pr.get("id"),
            "title": title,
            "acceptance": list(pr.get("acceptance") or []),
            "notes": list(pr.get("notes") or []),
            "labels": list(pr.get("labels") or []),
            "guidance": dict(pr.get("guidance") or {}),
        }
        sub_content = sub_template.render(
            wave=wave,
            pr=normalized,
            generated_at=generated_at,
            timezone_label=label.context,
        )
        sub_path = subprompt_root / f"{slug}.md"
        _write_text(sub_path, sub_content)

        body_without_heading = "\n".join(sub_content.splitlines()[1:]).lstrip()
        summary_line = (
            "Generated automatically from "
            f"backlog/wave{wave}.yaml on {generated_at} {label.parenthetical}."
        )
        issue_content = issue_template.render(
            wave=wave,
            pr=normalized,
            summary_line=summary_line,
            subprompt_body=body_without_heading,
            timezone_label=label.summary,
        )
        issue_path = issue_root / f"{slug}.md"
        _write_text(issue_path, issue_content)

        items.append(
            {
                "title": normalized["title"],
                "slug": slug,
                "labels": normalized["labels"],
                "acceptance": normalized["acceptance"],
                "subprompt_path": sub_path.relative_to(root).as_posix(),
                "issue_path": issue_path.relative_to(root).as_posix(),
                "id": normalized.get("id"),
            }
        )
    return items


def write_manifest(
    wave: int,
    items: list[dict[str, Any]],
    *,
    generated_at: str,
    base_dir: Path | None = None,
    timezone: str = PHOENIX_TZ,
) -> Path:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    manifest_dir = root / "artifacts" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"wave{wave}_subprompts.json"
    payload = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "timezone": timezone,
        "git_sha": os.getenv("GIT_SHA", "GIT_SHA_HERE"),
        "items": sorted(items, key=lambda item: item["slug"]),
    }
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _write_text(manifest_path, content)
    return manifest_path


def generate_from_yaml(
    spec_path: Path | str,
    *,
    base_dir: Path | None = None,
    timezone: str = PHOENIX_TZ,
    archive_previous: bool = True,
    now: Callable[[], datetime] | None = None,
) -> GeneratorResult:
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    spec_path = Path(spec_path)
    if not spec_path.is_absolute():
        spec_path = root / spec_path
    spec = load_spec(spec_path)
    now_provider = now or (lambda: zoned_now(timezone))
    current_dt = now_provider()
    generated_at = resolve_generated_at(spec["wave"], base_dir=root, fallback=current_dt)
    label = format_timezone_label(timezone)

    archive_result: ArchiveResult | None = None
    if archive_previous:
        archive_result = archive_previous_wave(
            spec["wave"], base_dir=root, timezone=timezone, now=current_dt
        )

    mop_path = render_mop_from_spec(
        spec,
        generated_at=generated_at,
        base_dir=root,
        timezone_label=label,
    )
    items = render_subprompts_and_issues(
        spec,
        generated_at=generated_at,
        base_dir=root,
        timezone_label=label,
    )
    manifest_path = write_manifest(
        spec["wave"],
        items,
        generated_at=generated_at,
        base_dir=root,
        timezone=timezone,
    )
    return GeneratorResult(
        mop_path=mop_path,
        manifest_path=manifest_path,
        items=items,
        generated_at=generated_at,
        archive=archive_result,
    )


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="releasecopilot-generator",
        description="Generate Wave artifacts from YAML specifications.",
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path("backlog/wave3.yaml"),
        help="Path to the wave YAML specification.",
    )
    parser.add_argument(
        "--timezone",
        default=PHOENIX_TZ,
        help="Timezone used when stamping artifacts (default: America/Phoenix).",
    )
    parser.add_argument(
        "--archive",
        "--no-archive",
        dest="archive",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Archive the previous wave MOP once per day.",
    )
    return parser


def run_cli(argv: Iterable[str]) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(list(argv))
    try:
        result = generate_from_yaml(
            args.spec,
            timezone=args.timezone,
            archive_previous=args.archive,
        )
    except Exception as exc:  # pragma: no cover - CLI entry guard
        parser.error(str(exc))
        return 1

    print(result.mop_path.as_posix())
    print(result.manifest_path.as_posix())
    return 0
