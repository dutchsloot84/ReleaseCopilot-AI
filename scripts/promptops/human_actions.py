"""Generate Wave 2 human action artifacts from the active MOP and prioritized issues."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Iterable, List, Sequence

from zoneinfo import ZoneInfo

PHOENIX_ZONE = ZoneInfo("America/Phoenix")


@dataclass(frozen=True)
class Issue:
    """Normalized representation of a prioritized issue."""

    number: int
    title: str
    url: str
    labels: Sequence[str]
    updated_at: datetime

    @property
    def workflow(self) -> str:
        title_lower = self.title.lower()
        if "orchestrator" in title_lower:
            return "Orchestrator Workflow"
        if "helper" in title_lower:
            return "Helpers Workflow"
        if "human" in title_lower:
            return "Human Oversight"
        return "General Oversight"


@dataclass(frozen=True)
class GenerationMetadata:
    author: str
    timestamp: datetime
    git_sha: str
    run_hash: str
    mop_path: Path
    issues_path: Path

    def to_header(self) -> str:
        phoenix_ts = format_phoenix_timestamp(self.timestamp)
        header = "---\n"
        header += f"author: {self.author}\n"
        header += f"phoenix_timestamp: {phoenix_ts}\n"
        header += f"git_sha: {self.git_sha}\n"
        header += f"run_hash: {self.run_hash}\n"
        header += "---\n"
        return header

    def to_json(self) -> dict:
        return {
            "author": self.author,
            "phoenix_timestamp": format_phoenix_timestamp(self.timestamp),
            "git_sha": self.git_sha,
            "run_hash": self.run_hash,
            "mop_source": self.mop_path.name,
            "issues_source": self.issues_path.name,
        }


def load_issues(issues_path: Path) -> List[Issue]:
    data = json.loads(issues_path.read_text(encoding="utf-8"))
    issues: List[Issue] = []
    for raw in data:
        updated_at = datetime.fromisoformat(raw["updatedAt"].replace("Z", "+00:00"))
        issues.append(
            Issue(
                number=int(raw["number"]),
                title=str(raw["title"]),
                url=str(raw["url"]),
                labels=tuple(sorted(raw.get("labels", []))),
                updated_at=updated_at,
            )
        )
    issues.sort(key=lambda issue: issue.number)
    return issues


def load_mop(mop_path: Path) -> str:
    if not mop_path.exists():
        raise FileNotFoundError(f"Wave 2 MOP not found: {mop_path}")
    return mop_path.read_text(encoding="utf-8")


def parse_prioritized_candidates(mop_text: str) -> dict[int, str]:
    lines = mop_text.splitlines()
    capture = False
    candidates: dict[int, str] = {}
    for line in lines:
        if line.strip().lower() == "## prioritized candidates for wave 2":
            capture = True
            continue
        if capture:
            if (
                line.startswith("##")
                and line.strip().lower() != "## prioritized candidates for wave 2"
            ):
                break
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("-"):
                continue
            text = stripped.lstrip("- ")
            number = extract_issue_number(text)
            if number is not None:
                candidates[number] = text
    return candidates


def parse_global_constraints(mop_text: str) -> List[str]:
    lines = mop_text.splitlines()
    capture = False
    constraints: List[str] = []
    for line in lines:
        if line.strip().lower() == "## global constraints":
            capture = True
            continue
        if capture:
            if (
                line.startswith("##")
                and line.strip().lower() != "## global constraints"
            ):
                break
            stripped = line.strip()
            if stripped.startswith("-"):
                constraints.append(stripped.lstrip("- ").strip())
            elif stripped == "":
                continue
            else:
                break
    return constraints


def extract_issue_number(text: str) -> int | None:
    import re

    match = re.search(r"#(\d+)", text)
    if match:
        return int(match.group(1))
    return None


def format_phoenix_timestamp(dt: datetime) -> str:
    if dt.tzinfo is None:
        raise ValueError(
            "Naive datetime values are not supported; provide an explicit timezone."
        )
    phoenix_dt = dt.astimezone(PHOENIX_ZONE)
    offset = phoenix_dt.utcoffset() or timedelta(0)
    offset_hours = int(offset.total_seconds() // 3600)
    return f"{phoenix_dt.isoformat()} America/Phoenix (UTC{offset_hours:+d})"


def format_issue_timestamp(issue: Issue) -> str:
    phoenix_dt = issue.updated_at.astimezone(PHOENIX_ZONE)
    return phoenix_dt.strftime("%Y-%m-%d %H:%M %Z (UTC%z)")


def compute_run_hash(
    mop_text: str,
    issues: Sequence[Issue],
    author: str,
    timestamp: datetime,
    git_sha: str,
) -> str:
    hasher = hashlib.sha256()
    hasher.update(mop_text.encode("utf-8"))
    issues_payload = [
        {
            "number": issue.number,
            "title": issue.title,
            "url": issue.url,
            "labels": list(issue.labels),
            "updated_at": issue.updated_at.isoformat(),
        }
        for issue in issues
    ]
    hasher.update(json.dumps(issues_payload, sort_keys=True).encode("utf-8"))
    hasher.update(author.encode("utf-8"))
    hasher.update(timestamp.isoformat().encode("utf-8"))
    hasher.update(git_sha.encode("utf-8"))
    return hasher.hexdigest()[:16]


def build_checklist(
    metadata: GenerationMetadata,
    issues: Sequence[Issue],
    candidate_map: dict[int, str],
    constraints: Sequence[str],
) -> str:
    sections: dict[str, List[Issue]] = {}
    for issue in issues:
        sections.setdefault(issue.workflow, []).append(issue)

    # Ensure deterministic section ordering.
    ordered_section_names = sorted(sections.keys())
    # Guarantee orchestrator/helpers even if empty.
    for required in ("Orchestrator Workflow", "Helpers Workflow"):
        if required not in ordered_section_names:
            ordered_section_names.append(required)
    ordered_section_names = sorted(
        set(ordered_section_names),
        key=lambda name: (
            (
                0
                if name == "Orchestrator Workflow"
                else 1 if name == "Helpers Workflow" else 2
            ),
            name,
        ),
    )

    lines: List[str] = [metadata.to_header(), "# Wave 2 Human Actions Checklist", ""]

    if constraints:
        lines.extend(["## Global Constraints Snapshot", ""])
        for constraint in constraints:
            lines.append(f"- {constraint}")
        lines.append("")

    for section_name in ordered_section_names:
        lines.append(f"## {section_name}")
        lines.append("")
        section_issues = sections.get(section_name, [])
        if not section_issues:
            lines.append(
                "- [ ] No prioritized issues supplied; coordinate with the Phoenix helpers to confirm scope."
            )
            lines.append("")
            continue
        for issue in section_issues:
            candidate_context = candidate_map.get(issue.number)
            lines.append(
                f"- [ ] Issue #{issue.number}: {issue.title} ({issue.url})\n"
                f"      - Last updated: {format_issue_timestamp(issue)}\n"
                f"      - Labels: {', '.join(issue.labels) or 'none'}"
            )
            if candidate_context:
                lines.append(f"      - MOP context: {candidate_context}")
            lines.append("")

    lines.append("## Manual Validation Notes")
    lines.append("")
    lines.append(
        "- Confirm artifact timestamps reflect America/Phoenix with no DST shifts (UTC-7 year-round)."
    )
    lines.append(
        "- Escalate blockers to the orchestrator DRI using the runbook contacts."
    )
    lines.append(
        "- Ensure no secrets or credentials were embedded in generated artifacts."
    )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_calendar(metadata: GenerationMetadata, issues: Sequence[Issue]) -> dict:
    base_date = metadata.timestamp.astimezone(PHOENIX_ZONE).date()
    dtstamp = metadata.timestamp.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    events: List[str] = []
    for idx, issue in enumerate(issues):
        start_date = datetime.combine(
            base_date, time(hour=9), tzinfo=PHOENIX_ZONE
        ) + timedelta(days=idx)
        end_date = start_date + timedelta(minutes=45)
        uid = f"{metadata.run_hash}-{issue.number}@releasecopilot"
        events.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"SUMMARY:Wave 2 review - {issue.title}",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART;TZID=America/Phoenix:{start_date.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND;TZID=America/Phoenix:{end_date.strftime('%Y%m%dT%H%M%S')}",
                f"DESCRIPTION:Review issue #{issue.number} ({issue.url}) with Phoenix helpers.",
                "END:VEVENT",
            ]
        )

    if not events:
        events.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{metadata.run_hash}-stub@releasecopilot",
                "SUMMARY:Wave 2 review - backlog alignment",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART;TZID=America/Phoenix:{base_date.strftime('%Y%m%dT090000')}",
                f"DTEND;TZID=America/Phoenix:{base_date.strftime('%Y%m%dT093000')}",
                "DESCRIPTION:Placeholder review block - no prioritized issues provided.",
                "END:VEVENT",
            ]
        )

    ical_lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//ReleaseCopilot//Wave2 Human Actions//EN",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-TIMEZONE:America/Phoenix",
        "BEGIN:VTIMEZONE",
        "TZID:America/Phoenix",
        "TZURL:https://www.iana.org/time-zones",
        "X-LIC-LOCATION:America/Phoenix",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:-0700",
        "TZOFFSETTO:-0700",
        "TZNAME:MST",
        "DTSTART:19700101T000000",
        "END:STANDARD",
        "END:VTIMEZONE",
        *events,
        "END:VCALENDAR",
    ]

    calendar = {
        "metadata": metadata.to_json(),
        "ical": "\n".join(ical_lines) + "\n",
    }
    return calendar


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def log_activity(
    metadata: GenerationMetadata, output_dir: Path, issue_numbers: Iterable[int]
) -> None:
    entry = {
        **metadata.to_json(),
        "timestamp": metadata.timestamp.astimezone(PHOENIX_ZONE).isoformat(),
        "issue_numbers": sorted(issue_numbers),
        "output_dir": output_dir.name,
    }
    log_path = output_dir / "activity.ndjson"
    existing: dict[str, dict] = {}
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            existing_key = f"{record.get('timestamp')}|{record.get('run_hash')}"
            existing[existing_key] = record
    entry_key = f"{entry['timestamp']}|{metadata.run_hash}"
    existing[entry_key] = entry
    sorted_records = sorted(
        existing.values(), key=lambda rec: (rec["timestamp"], rec.get("run_hash", ""))
    )
    log_path.write_text(
        "\n".join(json.dumps(rec, sort_keys=True) for rec in sorted_records) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Wave 2 human action artifacts."
    )
    parser.add_argument(
        "--mop-path",
        type=Path,
        default=Path("project/mop/wave2_mop.md"),
        help="Path to the Wave 2 MOP markdown file.",
    )
    parser.add_argument(
        "--issues-path",
        type=Path,
        default=Path("artifacts/top_issues.json"),
        help="Path to the prioritized issues JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/human-actions"),
        help="Directory where generated artifacts are written.",
    )
    parser.add_argument(
        "--author",
        default="PromptOps Automation",
        help="Author metadata for the artifacts.",
    )
    parser.add_argument(
        "--timestamp",
        help="ISO8601 timestamp to use for metadata (defaults to current Phoenix time).",
    )
    parser.add_argument(
        "--git-sha", default="unknown", help="Git SHA to embed in artifact metadata."
    )
    return parser.parse_args(argv)


def resolve_timestamp(timestamp_str: str | None) -> datetime:
    if timestamp_str:
        parsed = datetime.fromisoformat(timestamp_str)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(PHOENIX_ZONE)
    return datetime.now(PHOENIX_ZONE)


def generate_human_actions(argv: Sequence[str] | None = None) -> GenerationMetadata:
    args = parse_args(argv)
    timestamp = resolve_timestamp(args.timestamp)

    mop_text = load_mop(args.mop_path)
    issues = load_issues(args.issues_path)
    run_hash = compute_run_hash(mop_text, issues, args.author, timestamp, args.git_sha)

    metadata = GenerationMetadata(
        author=args.author,
        timestamp=timestamp,
        git_sha=args.git_sha,
        run_hash=run_hash,
        mop_path=args.mop_path,
        issues_path=args.issues_path,
    )

    candidate_map = parse_prioritized_candidates(mop_text)
    constraints = parse_global_constraints(mop_text)

    checklist = build_checklist(metadata, issues, candidate_map, constraints)
    checklist_path = args.output_dir / "checklist.md"
    write_text(checklist_path, checklist)

    calendar = build_calendar(metadata, issues)
    calendar_path = args.output_dir / "calendar.json"
    write_json(calendar_path, calendar)

    log_activity(metadata, args.output_dir, (issue.number for issue in issues))

    return metadata


def main() -> None:
    generate_human_actions()


if __name__ == "__main__":
    main()
