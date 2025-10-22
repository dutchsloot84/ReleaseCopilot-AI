"""Wave 2 helper automation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Iterable, Sequence
import uuid

import click
from jinja2 import Environment, FileSystemLoader
from slugify import slugify  # type: ignore[import-untyped]
import yaml

from releasecopilot.logging_config import get_logger
from tools.generator.generator import TimezoneLabel, format_timezone_label

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PHOENIX_TZ = "America/Phoenix"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
MANIFEST_SCHEMA_VERSION = "1.0"


logger = get_logger(__name__)


def phoenix_now() -> datetime:
    """Return the current Phoenix-aware datetime."""

    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(PHOENIX_TZ)).replace(microsecond=0)


@dataclass
class Wave2HelperConfig:
    """Configuration payload for the Wave 2 helper automation."""

    label_weights: dict[str, int] = field(default_factory=dict)
    maintainers: list[str] = field(default_factory=list)
    target_labels: list[str] = field(default_factory=list)
    artifact_dirs: dict[str, str] = field(default_factory=dict)
    mop_constraints: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Wave2HelperConfig":
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        return cls(
            label_weights={
                (key or "").lower(): int(value)
                for key, value in (payload.get("label_weights") or {}).items()
            },
            maintainers=list(payload.get("maintainers", [])),
            target_labels=[(label or "").lower() for label in payload.get("target_labels", [])],
            artifact_dirs={
                key: str(value) for key, value in (payload.get("artifact_dirs") or {}).items()
            },
            mop_constraints=dict(payload.get("mop_constraints", {})),
        )

    def artifact_path(self, key: str) -> Path:
        try:
            value = self.artifact_dirs[key]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Missing artifact directory for '{key}'") from exc

        path = Path(value)
        if key == "base":
            return path

        if not path.is_absolute():
            base_dir = self.artifact_dirs.get("base")
            if base_dir:
                path = Path(base_dir) / path
        return path

    @property
    def timezone(self) -> str:
        return str(self.mop_constraints.get("timezone", PHOENIX_TZ))

    @property
    def markers(self) -> Sequence[str]:
        markers = self.mop_constraints.get("markers") or ["Decision", "Note", "Action"]
        return tuple(markers)


@dataclass
class Issue:
    """Simplified GitHub issue representation."""

    number: int
    title: str
    url: str
    body: str
    labels: list[str]
    score: int = 0

    @classmethod
    def from_raw(cls, payload: dict[str, Any]) -> "Issue":
        labels: list[str] = []
        for entry in payload.get("labels", []):
            if isinstance(entry, str):
                labels.append(entry)
            else:
                labels.append(str(entry.get("name", "")).strip())
        raw_number = payload.get("number")
        number = int(raw_number) if raw_number is not None else 0
        return cls(
            number=number,
            title=str(payload.get("title", "")).strip(),
            url=str(payload.get("html_url") or payload.get("url") or ""),
            body=str(payload.get("body", "")),
            labels=[label for label in labels if label],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "body": self.body,
            "labels": list(self.labels),
            "score": self.score,
        }


class Wave2Helper:
    """Primary interface for helper automation tasks."""

    def __init__(
        self,
        config: Wave2HelperConfig,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self._now = now_provider or phoenix_now
        self.logger = logger

    def filter_issues(self, issues: Iterable[Issue]) -> list[Issue]:
        target = {label.lower() for label in self.config.target_labels}
        filtered: list[Issue] = []
        for issue in issues:
            labels = {label.lower() for label in issue.labels}
            if target and not labels.intersection(target):
                continue
            filtered.append(issue)
        self.logger.info(
            "Filtered issues",
            extra={
                "command": "collect",
                "count": len(filtered),
                "target_labels": sorted(target),
            },
        )
        return filtered

    def prioritize(self, issues: Iterable[Issue]) -> list[Issue]:
        weights = self.config.label_weights
        default_weight = int(weights.get("default", 0))
        prioritized: list[Issue] = []
        for issue in issues:
            score = 0
            for label in issue.labels:
                score += int(weights.get(label.lower(), default_weight))
            issue.score = score
            prioritized.append(issue)
        prioritized.sort(key=lambda issue: (-issue.score, issue.number))
        self.logger.info(
            "Prioritized issues",
            extra={
                "command": "prioritize",
                "count": len(prioritized),
                "top_issue": prioritized[0].number if prioritized else None,
            },
        )
        return prioritized

    def write_prioritized_artifact(self, issues: list[Issue]) -> Path:
        generated_at = self._now().isoformat()
        payload = {
            "metadata": {
                "generated_at": generated_at,
                "timezone": self.config.timezone,
                "maintainers": list(self.config.maintainers),
            },
            "issues": [issue.to_dict() for issue in issues],
        }
        path = self.config.artifact_path("prioritized")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.logger.info(
            "Wrote prioritized issues",
            extra={
                "command": "prioritize",
                "artifact": str(path),
                "generated_at": generated_at,
            },
        )
        self._record_activity("prioritize", {"artifact": str(path)})
        return path

    def seed_prompts(self, issues: Iterable[Issue]) -> list[Path]:
        generated_at = self._now().isoformat()
        markers = ", ".join(self.config.markers)
        prompt_dir = self.config.artifact_path("prompts_dir")
        prompt_dir.mkdir(parents=True, exist_ok=True)
        created_paths: list[Path] = []
        for issue in issues:
            filename = self._build_prompt_filename(issue)
            path = prompt_dir / filename
            content = self._render_prompt(issue, generated_at, markers)
            path.write_text(content, encoding="utf-8")
            created_paths.append(path)
        self.logger.info(
            "Seeded prompts",
            extra={
                "command": "seed",
                "count": len(created_paths),
                "timezone": self.config.timezone,
            },
        )
        self._record_activity("seed", {"files": [str(path) for path in created_paths]})
        return created_paths

    def prepare_comments(self, issues: Iterable[Issue]) -> list[Path]:
        comments_dir = self.config.artifact_path("comments")
        comments_dir.mkdir(parents=True, exist_ok=True)
        generated_at = self._now().isoformat()
        created: list[Path] = []
        for issue in issues:
            path = comments_dir / f"{issue.number}.md"
            content = self._render_comment(issue, generated_at)
            path.write_text(content, encoding="utf-8")
            created.append(path)
        self.logger.info(
            "Prepared comment drafts",
            extra={
                "command": "post",
                "count": len(created),
                "comments_dir": str(comments_dir),
            },
        )
        self._record_activity("post", {"files": [str(path) for path in created]})
        return created

    def scaffold_pr_template(self, issues: Sequence[Issue]) -> Path:
        path = self.config.artifact_path("pr_template")
        path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = self._now().isoformat()
        primary = issues[0] if issues else None
        branch_name = self._build_branch_name(primary)
        body = self._render_pr_body(generated_at, branch_name, primary, issues)
        path.write_text(body, encoding="utf-8")
        self.logger.info(
            "Scaffolded PR template",
            extra={"command": "open-pr", "template": str(path), "branch": branch_name},
        )
        self._record_activity("open-pr", {"template": str(path), "branch": branch_name})
        return path

    def write_collected_issues(self, issues: Iterable[Issue]) -> Path:
        path = self.config.artifact_path("collected_issues")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [issue.to_dict() for issue in issues]
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        self.logger.info(
            "Persisted collected issues",
            extra={"command": "collect", "artifact": str(path), "count": len(payload)},
        )
        self._record_activity("collect", {"artifact": str(path), "count": len(payload)})
        return path

    def _build_prompt_filename(self, issue: Issue) -> str:
        slug = "_".join(self._normalize_token(token) for token in issue.title.split())
        return f"{issue.number}_{slug}.md"

    def _render_prompt(self, issue: Issue, generated_at: str, markers: str) -> str:
        label_text = ", ".join(issue.labels) or "(none)"
        maintainers = ", ".join(self.config.maintainers) or "(unassigned)"
        return (
            f"# Wave 2 – Sub-Prompt · [{issue.number}] {issue.title}\n\n"
            "**Context:** Generated from the active Wave 2 MOP. Honor the Phoenix timezone "
            f"({self.config.timezone}) and preserve deterministic artifacts with explicit markers ({markers}).\n\n"
            f"**Issue Snapshot ({generated_at})**\n"
            f"- URL: {issue.url}\n"
            f"- Labels: {label_text}\n"
            f"- Maintainers: {maintainers}\n\n"
            "## Wave 2 Constraints\n"
            "- Uphold Decision / Note / Action sections in deliverables.\n"
            "- Schedule follow-ups with Phoenix-aware timestamps.\n"
            "- Avoid direct network calls during offline validation.\n\n"
            "## Helper Tasks\n"
            f"- [ ] Confirm backlog details for issue #{issue.number}.\n"
            "- [ ] Update artifacts/helpers after implementing automation updates.\n"
            "- [ ] Document Phoenix scheduling considerations in docs and changelog.\n"
        )

    def _render_comment(self, issue: Issue, generated_at: str) -> str:
        return (
            "<!-- wave2-helper comment draft -->\n"
            f"**Decision:** _Summarize next steps for #{issue.number}._\n\n"
            "**Note:** _Add Phoenix scheduling context (America/Phoenix) before posting._\n\n"
            "**Action:** _List manual follow-ups tied to deterministic artifacts._\n\n"
            f"_Draft generated {generated_at} ({self.config.timezone})._"
        )

    def _render_pr_body(
        self,
        generated_at: str,
        branch_name: str,
        primary: Issue | None,
        issues: Sequence[Issue],
    ) -> str:
        lines = ["<!-- wave2-helper PR template -->"]
        lines.append(f"# Draft: Wave 2 Helper Automation ({generated_at})")
        lines.append("")
        lines.append("## Summary")
        if primary:
            lines.append(f"- Aligns with #{primary.number} – {primary.title}.")
        else:
            lines.append("- Backlog automation support tasks.")
        lines.append("- Ensures Phoenix-local scheduling context and deterministic artifacts.")
        lines.append("")
        lines.append("## Testing")
        lines.append("- [ ] `pytest tests/github/test_wave2_helper.py` (offline)")
        lines.append("- [ ] `pytest tests/ops/test_helper_cli.py` (offline)")
        lines.append("")
        lines.append("## Metadata")
        lines.append(f"- Suggested branch: `{branch_name}`")
        lines.append(f"- Generated: {generated_at} ({self.config.timezone})")
        if issues:
            lines.append("- Related issues:")
            for issue in issues:
                lines.append(f"  - #{issue.number} – {issue.title} ({issue.url})")
        else:
            lines.append("- No related issues captured in this run.")
        return "\n".join(lines)

    def _build_branch_name(self, issue: Issue | None) -> str:
        if not issue:
            return "wave2/helper-automation"
        slug = "-".join(
            token
            for token in (self._normalize_token(part) for part in issue.title.split())
            if token
        )
        return f"wave2/{issue.number}-{slug or 'helper'}"

    def _normalize_token(self, value: str) -> str:
        return "".join(ch for ch in value if ch.isalnum()).lower()

    def _record_activity(self, command: str, metadata: dict[str, Any]) -> None:
        timestamp = self._now().isoformat()
        entry = {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{command}:{timestamp}")),
            "command": command,
            "timestamp": timestamp,
            "timezone": self.config.timezone,
        }
        entry.update(metadata)
        path = self.config.artifact_path("activity_log")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")


def _load_issues_from_json(path: Path) -> list[Issue]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Issue.from_raw(item) for item in payload]


def _gh_issue_list(labels: list[str]) -> list[Issue]:
    token_present = bool(os.getenv("GITHUB_TOKEN"))
    logger.info(
        "Invoking gh issue list",
        extra={"command": "collect", "token_present": token_present, "labels": labels},
    )
    cmd = [
        "gh",
        "issue",
        "list",
        "--state",
        "open",
        "--json",
        "number,title,labels,htmlUrl,body",
    ]
    if labels:
        cmd.extend(["--label", ",".join(labels)])
    result = subprocess.run(cmd, capture_output=True, check=True, text=True)
    payload = json.loads(result.stdout or "[]")
    return [Issue.from_raw(item) for item in payload]


def _jinja_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def write_text(path: Path, content: str) -> Path:
    """Write text to ``path`` only when the content differs."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return path
    path.write_text(content, encoding="utf-8")
    return path


def load_spec(path: Path | str) -> dict[str, Any]:
    """Load a wave specification from YAML."""

    spec_path = Path(path)
    with spec_path.open("r", encoding="utf-8") as handle:
        raw_spec = yaml.safe_load(handle) or {}
    try:
        wave = int(raw_spec["wave"])
    except KeyError as exc:  # pragma: no cover - validation guard
        raise ValueError("Missing required 'wave' field in spec") from exc

    def _stringify_list(values: Iterable[Any]) -> list[str]:
        result: list[str] = []
        for entry in values:
            if isinstance(entry, dict):
                result.append(", ".join(f"{key}: {value}" for key, value in entry.items()))
            else:
                result.append(str(entry))
        return result

    def _normalize_guidance(payload: Any) -> dict[str, str]:
        guidance: dict[str, str] = {}
        if not isinstance(payload, dict):
            return guidance
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, list):
                text = "\n".join(str(item) for item in value if item is not None)
            else:
                text = str(value)
            guidance[key] = text
        return guidance

    spec = {
        "wave": wave,
        "purpose": str(raw_spec.get("purpose", "")).strip(),
        "constraints": _stringify_list(raw_spec.get("constraints") or []),
        "quality_bar": _stringify_list(raw_spec.get("quality_bar") or []),
    }
    sequenced: list[dict[str, Any]] = []
    for pr in raw_spec.get("sequenced_prs", []) or []:
        sequenced.append(
            {
                "title": str(pr.get("title", "")).strip(),
                "acceptance": _stringify_list(pr.get("acceptance") or []),
                "notes": _stringify_list(pr.get("notes") or []),
                "labels": _stringify_list(pr.get("labels") or []),
                "guidance": _normalize_guidance(pr.get("guidance")),
            }
        )
    spec["sequenced_prs"] = sequenced
    return spec


def archive_previous_wave_mop(prev_wave: int) -> None:
    """Archive the prior wave's MOP once per Phoenix day."""

    if prev_wave <= 0:
        return
    source = Path("docs/mop") / f"mop_wave{prev_wave}.md"
    if not source.exists():
        return
    archive_dir = Path("docs/mop/archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = phoenix_now().date().isoformat()
    destination = archive_dir / f"mop_wave{prev_wave}_{timestamp}.md"
    if destination.exists():
        return
    shutil.copy2(source, destination)


def render_mop_from_yaml(
    spec: dict[str, Any],
    generated_at: str | None = None,
    timezone_label: TimezoneLabel | None = None,
) -> Path:
    """Render the Mission Outline Plan from the YAML spec."""

    env = _jinja_environment()
    template = env.get_template("mop.md.j2")
    timestamp = generated_at or phoenix_now().isoformat()
    label = timezone_label or format_timezone_label(PHOENIX_TZ)
    content = template.render(
        wave=spec["wave"],
        purpose=spec.get("purpose", ""),
        constraints=spec.get("constraints", []),
        quality_bar=spec.get("quality_bar", []),
        sequenced_prs=spec.get("sequenced_prs", []),
        generated_at=timestamp,
        timezone_parenthetical=label.parenthetical,
    )
    path = Path("docs/mop") / f"mop_wave{spec['wave']}.md"
    write_text(path, content)
    return path


def render_subprompts_and_issues(
    spec: dict[str, Any],
    generated_at: str | None = None,
    timezone_label: TimezoneLabel | None = None,
) -> list[dict[str, Any]]:
    """Render sub-prompts and issue bodies for each sequenced PR."""

    env = _jinja_environment()
    sub_template = env.get_template("subprompt.md.j2")
    issue_template = env.get_template("issue_body.md.j2")
    wave = spec["wave"]
    timestamp = generated_at or phoenix_now().isoformat()
    label = timezone_label or format_timezone_label(PHOENIX_TZ)
    subprompt_root = Path("docs/sub-prompts") / f"wave{wave}"
    issue_root = Path("artifacts/issues") / f"wave{wave}"
    items: list[dict[str, Any]] = []
    for pr in spec.get("sequenced_prs", []):
        title = pr.get("title", "")
        slug = slugify(title) or f"wave{wave}-item"
        normalized = {
            "title": title,
            "acceptance": list(pr.get("acceptance") or []),
            "notes": list(pr.get("notes") or []),
            "labels": list(pr.get("labels") or []),
            "guidance": dict(pr.get("guidance") or {}),
        }
        subprompt_content = sub_template.render(
            wave=wave,
            pr=normalized,
            generated_at=timestamp,
            timezone_label=label.context,
        )
        lines = subprompt_content.splitlines()
        body_without_heading = "\n".join(lines[1:]).lstrip()
        summary_line = (
            "Generated automatically from backlog/wave"
            f"{wave}.yaml on {timestamp} {label.parenthetical}."
        )
        issue_content = issue_template.render(
            wave=wave,
            pr=normalized,
            summary_line=summary_line,
            subprompt_body=body_without_heading,
            timezone_label=label.summary,
        )
        subprompt_path = subprompt_root / f"{slug}.md"
        issue_path = issue_root / f"{slug}.md"
        write_text(subprompt_path, subprompt_content)
        write_text(issue_path, issue_content)
        items.append(
            {
                "title": normalized["title"],
                "slug": slug,
                "labels": normalized["labels"],
                "acceptance": normalized["acceptance"],
                "subprompt_path": subprompt_path.as_posix(),
                "issue_path": issue_path.as_posix(),
            }
        )
    return items


def write_manifest(wave: int, items: list[dict[str, Any]], generated_at: str | None = None) -> Path:
    """Write the manifest describing generated sub-prompts."""

    manifest_path = Path("artifacts/manifests") / f"wave{wave}_subprompts.json"
    timestamp = generated_at or phoenix_now().isoformat()
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": timestamp,
        "timezone": PHOENIX_TZ,
        "git_sha": os.getenv("GIT_SHA", "GIT_SHA_HERE"),
        "items": sorted(items, key=lambda item: item["slug"]),
    }
    write_text(
        manifest_path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    return manifest_path


def resolve_generated_at(wave: int) -> str:
    """Return a deterministic Phoenix timestamp for the given wave."""

    manifest_path = Path("artifacts/manifests") / f"wave{wave}_subprompts.json"
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:  # pragma: no cover - defensive guard
            payload = {}
        existing = payload.get("generated_at")
        if isinstance(existing, str) and existing.strip():
            return existing
    return phoenix_now().isoformat()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("config/wave2_helper.yml"),
    show_default=True,
)
@click.pass_context
def cli(ctx: click.Context, config_path: Path) -> None:
    """Wave 2 helper automation entry point."""

    ctx.ensure_object(dict)
    ctx.obj["config"] = Wave2HelperConfig.load(config_path)
    ctx.obj["helper"] = Wave2Helper(ctx.obj["config"])


@cli.command()
@click.option(
    "--issues-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Offline JSON payload containing issue metadata.",
)
@click.pass_context
def collect(ctx: click.Context, issues_json: Path | None) -> None:
    """Collect Wave 2 backlog issues."""

    helper: Wave2Helper = ctx.obj["helper"]
    config: Wave2HelperConfig = ctx.obj["config"]
    if issues_json:
        issues = _load_issues_from_json(issues_json)
    else:
        issues = _gh_issue_list(config.target_labels)
    filtered = helper.filter_issues(issues)
    artifact = helper.write_collected_issues(filtered)
    click.echo(str(artifact))


@cli.command()
@click.option(
    "--issues-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON file containing issues to prioritize.",
)
@click.pass_context
def prioritize(ctx: click.Context, issues_json: Path | None) -> None:
    """Prioritize collected issues and emit artifacts."""

    helper: Wave2Helper = ctx.obj["helper"]
    config: Wave2HelperConfig = ctx.obj["config"]
    if issues_json:
        issues = _load_issues_from_json(issues_json)
    else:
        path = config.artifact_path("collected_issues")
        if not path.exists():
            raise click.UsageError(
                "No collected issues found. Run 'collect' first or pass --issues-json."
            )
        issues = _load_issues_from_json(path)
    prioritized = helper.prioritize(issues)
    artifact = helper.write_prioritized_artifact(prioritized)
    click.echo(str(artifact))


@cli.command()
@click.option(
    "--issues-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON file containing prioritized issues.",
)
@click.pass_context
def seed(ctx: click.Context, issues_json: Path | None) -> None:
    """Seed prompt templates from prioritized issues."""

    helper: Wave2Helper = ctx.obj["helper"]
    config: Wave2HelperConfig = ctx.obj["config"]
    if issues_json:
        issues = _load_issues_from_json(issues_json)
    else:
        path = config.artifact_path("prioritized")
        if not path.exists():
            raise click.UsageError(
                "No prioritized issues found. Run 'prioritize' first or pass --issues-json."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        issues = [Issue.from_raw(item) for item in payload.get("issues", [])]
    helper.seed_prompts(issues)


@cli.command()
@click.option(
    "--issues-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON file containing prioritized issues.",
)
@click.pass_context
def post(ctx: click.Context, issues_json: Path | None) -> None:
    """Prepare comment drafts for manual posting."""

    helper: Wave2Helper = ctx.obj["helper"]
    config: Wave2HelperConfig = ctx.obj["config"]
    issues = _resolve_issues_for_artifacts(config, issues_json)
    helper.prepare_comments(issues)


@cli.command(name="open-pr")
@click.option(
    "--issues-json",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="JSON file containing prioritized issues.",
)
@click.pass_context
def open_pr(ctx: click.Context, issues_json: Path | None) -> None:
    """Scaffold a local PR template based on prioritized issues."""

    helper: Wave2Helper = ctx.obj["helper"]
    config: Wave2HelperConfig = ctx.obj["config"]
    issues = _resolve_issues_for_artifacts(config, issues_json)
    helper.scaffold_pr_template(issues)


@cli.command(name="generate")
@click.argument("spec", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--archive/--no-archive",
    "archive_previous",
    default=True,
    show_default=True,
    help="Archive the previous wave MOP before rendering the new one.",
)
def generate(spec: Path, archive_previous: bool) -> None:
    """Generate wave artifacts from the YAML specification."""

    payload = load_spec(spec)
    if archive_previous:
        archive_previous_wave_mop(payload["wave"] - 1)
    timestamp = resolve_generated_at(payload["wave"])
    mop_path = render_mop_from_yaml(payload, generated_at=timestamp)
    items = render_subprompts_and_issues(payload, generated_at=timestamp)
    manifest_path = write_manifest(payload["wave"], items, generated_at=timestamp)
    click.echo(str(mop_path))
    click.echo(str(manifest_path))


def _resolve_issues_for_artifacts(
    config: Wave2HelperConfig, issues_json: Path | None
) -> list[Issue]:  # pragma: no cover - convenience wrapper
    if issues_json:
        return _load_issues_from_json(issues_json)
    path = config.artifact_path("prioritized")
    if not path.exists():
        raise click.UsageError(
            "No prioritized issues found. Run 'prioritize' first or pass --issues-json."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Issue.from_raw(item) for item in payload.get("issues", [])]


def main() -> None:  # pragma: no cover - CLI shim
    cli()


if __name__ == "__main__":  # pragma: no cover
    main()
