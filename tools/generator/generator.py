"""Core Wave generator orchestration utilities."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
import json
import os
from pathlib import Path
import re
from types import ModuleType
from typing import Any, Callable, Final, Iterable, Mapping
from zoneinfo import ZoneInfo

try:  # pragma: no cover - optional dependency for full YAML parsing
    yaml: ModuleType | None = import_module("yaml")
except ModuleNotFoundError:  # pragma: no cover - exercised in hook environments
    yaml = None

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


def _slugify(text: str) -> str:
    normalized = text.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")


def _fold_block(lines: list[str]) -> str:
    if not lines:
        return ""
    segments: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if not line.strip():
            if buffer:
                segments.append(" ".join(buffer).strip())
                buffer = []
            segments.append("")
        else:
            buffer.append(line.strip())
    if buffer:
        segments.append(" ".join(buffer).strip())
    result_lines: list[str] = []
    for segment in segments:
        if segment == "":
            result_lines.append("")
        else:
            result_lines.append(segment)
    return "\n".join(result_lines)


def _literal_block(lines: list[str]) -> str:
    if not lines:
        return ""
    return "\n".join(lines)


def _parse_scalar(token: str) -> Any:
    lowered = token.lower()
    if lowered in {"null", "none"}:
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if token.isdigit():
        return int(token)
    try:
        return float(token)
    except ValueError:
        pass
    if token.startswith(("'", '"')) and token.endswith(("'", '"')):
        return token[1:-1]
    return token


def _collect_block(lines: list[str], start: int, indent: int) -> tuple[list[str], int]:
    collected: list[str] = []
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            collected.append("")
            index += 1
            continue
        current_indent = len(raw) - len(raw.lstrip(" "))
        if current_indent < indent:
            break
        collected.append(raw[indent:])
        index += 1
    return collected, index


def _parse_block(lines: list[str], start: int, indent: int) -> tuple[Any, int]:
    mapping: dict[str, Any] = {}
    sequence: list[Any] | None = None
    index = start
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        current_indent = len(raw) - len(raw.lstrip(" "))
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError("Invalid indentation in YAML-like specification")
        if stripped.startswith("- "):
            if mapping:
                raise ValueError("Mixed mapping and sequence not supported")
            if sequence is None:
                sequence = []
            item_content = stripped[2:]
            item_indent = indent + 2
            index += 1
            if not item_content:
                value, index = _parse_block(lines, index, item_indent)
                sequence.append(value)
                continue
            if item_content.endswith(":") or ":" in item_content:
                key_part, _, value_part = item_content.partition(":")
                key = key_part.strip()
                value_part = value_part.strip()
                item_dict: dict[str, Any] = {}
                if value_part:
                    item_dict[key] = _parse_scalar(value_part)
                else:
                    nested_value, index = _parse_block(lines, index, item_indent + 2)
                    item_dict[key] = nested_value
                while index < len(lines):
                    lookahead = lines[index]
                    lookahead_stripped = lookahead.strip()
                    if not lookahead_stripped:
                        index += 1
                        continue
                    la_indent = len(lookahead) - len(lookahead.lstrip(" "))
                    if la_indent < item_indent:
                        break
                    if la_indent > item_indent:
                        raise ValueError("Invalid nested indentation in sequence item")
                    if lookahead_stripped.startswith("- "):
                        break
                    key2_part, _, value2_part = lookahead_stripped.partition(":")
                    key2 = key2_part.strip()
                    value2_part = value2_part.strip()
                    index += 1
                    if value2_part in {"|", "|-", ">", ">-"}:
                        block_lines, index = _collect_block(lines, index, item_indent + 2)
                        if value2_part.startswith(">"):
                            item_dict[key2] = _fold_block(block_lines)
                        else:
                            item_dict[key2] = _literal_block(block_lines)
                        continue
                    if not value2_part:
                        nested_value2, index = _parse_block(lines, index, item_indent + 2)
                        item_dict[key2] = nested_value2
                    else:
                        item_dict[key2] = _parse_scalar(value2_part)
                sequence.append(item_dict)
                continue
            sequence.append(_parse_scalar(item_content))
            continue
        key_part, _, value_part = stripped.partition(":")
        key = key_part.strip()
        value_part = value_part.strip()
        index += 1
        if value_part in {"|", "|-", ">", ">-"}:
            block_lines, index = _collect_block(lines, index, indent + 2)
            if value_part.startswith(">"):
                mapping[key] = _fold_block(block_lines)
            else:
                mapping[key] = _literal_block(block_lines)
            continue
        if not value_part:
            value, index = _parse_block(lines, index, indent + 2)
            mapping[key] = value
        else:
            mapping[key] = _parse_scalar(value_part)
    if sequence is not None:
        return sequence, index
    return mapping, index


def _simple_yaml_load(text: str) -> Any:
    lines = text.splitlines()
    value, index = _parse_block(lines, 0, 0)
    if index < len(lines):
        remaining = any(line.strip() for line in lines[index:])
        if remaining:
            raise ValueError("Failed to consume entire YAML specification")
    return value


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return path
    if not content.endswith("\n"):
        content = f"{content}\n"
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
        raw_text = handle.read()
    if yaml is not None:
        raw_spec = yaml.safe_load(raw_text) or {}
    else:
        raw_spec = _simple_yaml_load(raw_text) or {}

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
    label = (timezone_label or format_timezone_label(PHOENIX_TZ)).parenthetical
    wave = spec["wave"]
    lines = [
        f"# Wave {wave} Mission Outline Plan",
        "",
        f"_Generated at {generated_at} {label}_",
        "",
        "## Purpose",
        str(spec.get("purpose", "")).strip(),
        "",
        "## Global Constraints",
    ]
    for item in spec.get("constraints", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Quality Bar",
        ]
    )
    for item in spec.get("quality_bar", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Sequenced PRs",
        ]
    )
    for pr in spec.get("sequenced_prs", []):
        title = pr.get("title", "")
        acceptance = list(pr.get("acceptance") or [])
        notes = list(pr.get("notes") or [])
        lines.append(f"- **{title}** — {len(acceptance)} acceptance checks")
        if acceptance:
            for check in acceptance:
                lines.append(f"  - {check}")
        if notes:
            lines.append("  _Notes:_")
            for note in notes:
                lines.append(f"  - {note}")
    lines.extend(
        [
            "",
            "## Artifacts & Traceability",
            f"- MOP source: `backlog/wave{wave}.yaml`",
            f"- Rendered MOP: `docs/mop/mop_wave{wave}.md`",
            f"- Sub-prompts: `docs/sub-prompts/wave{wave}/`",
            f"- Issue bodies: `artifacts/issues/wave{wave}/`",
            f"- Manifest: `artifacts/manifests/wave{wave}_subprompts.json`",
            f"- Generated via `make gen-wave{wave}` with Phoenix timestamps.",
            "",
            "## Notes & Decisions Policy",
            "- Capture contributor annotations with **Decision:**/**Note:**/**Action:** markers.",
            "- America/Phoenix (no DST) timestamps must accompany status updates.",
            "- Store generated artifacts in Git with deterministic ordering.",
            "",
            "## Acceptance Gate",
            "- Validate linting, typing, and tests before marking this wave complete.",
            "- Ensure the manifest SHA (`git_sha`) matches the release commit used for generation.",
        ]
    )
    content = "\n".join(lines)
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
    wave = spec["wave"]
    label = timezone_label or format_timezone_label(PHOENIX_TZ)
    subprompt_root = root / "docs" / "sub-prompts" / f"wave{wave}"
    issue_root = root / "artifacts" / "issues" / f"wave{wave}"
    items: list[dict[str, Any]] = []
    for pr in spec.get("sequenced_prs", []):
        title = pr.get("title", "")
        slug = _slugify(title) or f"wave{wave}-item"
        normalized = {
            "id": pr.get("id"),
            "title": title,
            "acceptance": list(pr.get("acceptance") or []),
            "notes": list(pr.get("notes") or []),
            "labels": list(pr.get("labels") or []),
            "guidance": dict(pr.get("guidance") or {}),
        }
        context_line = (
            "This task originates from the Wave {wave} Mission Outline Plan generated from YAML. "
            "Honor {tz} for all scheduling data and reference the Decision/Note/Action markers when "
            "updating artifacts."
        ).format(wave=wave, tz=label.context)
        sub_lines = [
            f"# Wave {wave} – Sub-Prompt · [AUTO] {normalized['title']}",
            "",
            "## Context",
            context_line,
            "",
            "## Acceptance Criteria (from issue)",
        ]
        for check in normalized["acceptance"]:
            sub_lines.append(f"- {check}")
        sub_lines.extend(
            [
                "",
                "## Return these 5 outputs",
                "1. Implementation plan covering sequencing and Phoenix-aware timestamps.",
                "2. Code snippets or diffs that satisfy the acceptance criteria.",
                "3. Tests (unit/pytest) demonstrating coverage.",
                "4. Documentation updates referencing this wave's artifacts.",
                "5. Risk assessment noting fallbacks and rollback steps.",
                "",
            ]
        )

        guidance = normalized["guidance"]

        def _append_guidance(key: str, heading: str) -> None:
            value = guidance.get(key)
            if value:
                sub_lines.append(heading)
                sub_lines.append(str(value).strip())
                sub_lines.append("")

        _append_guidance("implementation_plan", "### Diff-oriented implementation plan")
        _append_guidance("code_snippets", "### Key code snippets")
        _append_guidance("tests", "### Tests (pytest; no live network)")
        _append_guidance("docs_excerpt", "### Docs excerpt (README/runbook)")
        _append_guidance("risk", "### Risk & rollback")

        sub_lines.append("")
        sub_lines.extend(
            [
                "## Critic Check",
                "- Re-read the acceptance criteria.",
                "- Confirm Phoenix timezone is referenced wherever scheduling appears.",
                "- Ensure no secrets or credentials are exposed.",
            ]
        )
        critic = guidance.get("critic_check")
        if critic:
            sub_lines.append(str(critic).strip())
        sub_lines.extend(
            [
                "",
                "## PR Markers",
                "- Begin change logs with **Decision:**/**Note:**/**Action:** blocks.",
                "- Link back to the generated manifest entry for traceability.",
            ]
        )
        markers = guidance.get("pr_markers")
        if markers:
            sub_lines.append(str(markers).strip())
        sub_content = "\n".join(sub_lines).rstrip() + "\n"
        sub_path = subprompt_root / f"{slug}.md"
        _write_text(sub_path, sub_content)

        body_without_heading = "\n".join(sub_content.splitlines()[1:]).lstrip()
        summary_line = (
            "Generated automatically from "
            f"backlog/wave{wave}.yaml on {generated_at} {label.parenthetical}."
        )
        labels_text = (
            ", ".join(normalized["labels"]) if normalized["labels"] else f"wave:wave{wave}"
        )
        issue_lines = [
            f"## {normalized['title']}",
            "",
            summary_line,
            "",
            body_without_heading.rstrip(),
            "",
            f"**Labels:** {labels_text}",
        ]
        issue_content = "\n".join(issue_lines)
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
