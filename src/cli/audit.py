"""Offline audit orchestration for the ``rc audit`` command."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any, Dict, Mapping

from config.loader import Defaults
from releasecopilot.logging_config import get_logger
from releasecopilot.uploader import upload_directory

from ..export.exporter import build_export_payload, export_all

LOGGER = get_logger(__name__)

REQUIRED_CACHE_FILES = {
    "stories": "stories.json",
    "commits": "commits.json",
    "links": "links.json",
    "summary": "summary.json",
}


class AuditInputError(RuntimeError):
    """Raised when expected cached payloads are missing or invalid."""


@dataclass(frozen=True)
class AuditOptions:
    cache_dir: Path
    json_path: Path
    excel_path: Path
    summary_path: Path
    scope: Mapping[str, str]
    upload_uri: str | None
    region: str | None
    dry_run: bool
    defaults: Defaults

    def build_plan(self) -> Dict[str, Any]:
        upload = None
        if self.upload_uri:
            bucket, prefix = parse_s3_uri(self.upload_uri)
            upload = {
                "bucket": bucket,
                "prefix": prefix,
                "region": self.region,
            }
        return {
            "cache_dir": str(self.cache_dir),
            "outputs": {
                "json": str(self.json_path),
                "excel": str(self.excel_path),
                "summary": str(self.summary_path),
            },
            "scope": dict(self.scope),
            "upload": upload,
            "defaults": self.defaults.as_dict(),
        }


@dataclass
class AuditResult:
    plan: Dict[str, Any]
    outputs: Dict[str, Path]
    uploaded: bool

    def as_dict(self) -> Dict[str, Any]:
        data = {
            "plan": self.plan,
            "outputs": {name: str(path) for name, path in self.outputs.items()},
            "uploaded": self.uploaded,
        }
        return data


def parse_s3_uri(value: str) -> tuple[str, str]:
    if not value.startswith("s3://"):
        raise AuditInputError("S3 destinations must use the s3://bucket/prefix format")
    remainder = value[5:]
    if not remainder:
        raise AuditInputError("S3 URI is missing a bucket name")
    parts = remainder.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket, prefix


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise AuditInputError(f"Required cache file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle) or {}
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise AuditInputError(f"Cache file {path} is not valid JSON") from exc


def load_cached_payloads(cache_dir: Path) -> Dict[str, Dict[str, Any]]:
    cache_dir = cache_dir.resolve()
    payloads: Dict[str, Dict[str, Any]] = {}
    for key, filename in REQUIRED_CACHE_FILES.items():
        path = cache_dir / filename
        payload = _load_json(path)
        payloads[key] = payload
        LOGGER.debug("Loaded cached payload", extra={"key": key, "path": str(path)})
    return payloads


def _build_export_payload(payloads: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    return build_export_payload(
        data={
            "summary": payloads.get("summary", {}),
            "stories_with_no_commits": payloads.get("stories", {}).get(
                "stories_with_no_commits", []
            ),
            "orphan_commits": payloads.get("commits", {}).get("orphan_commits", []),
            "commit_story_mapping": payloads.get("links", {}).get("commit_story_mapping", []),
        }
    )


def run_audit(options: AuditOptions) -> AuditResult:
    plan = options.build_plan()
    LOGGER.info(
        "Starting offline audit",
        extra={"cache_dir": plan["cache_dir"], "scope": plan["scope"]},
    )

    payloads = load_cached_payloads(options.cache_dir)
    payload = _build_export_payload(payloads)

    filenames = {
        "json": options.json_path,
        "excel": options.excel_path,
        "summary": options.summary_path,
    }
    outputs = export_all(
        payload,
        out_dir=None,
        formats=options.defaults.export_formats,
        filenames=filenames,
    )

    uploaded = False
    if options.upload_uri:
        bucket, prefix = parse_s3_uri(options.upload_uri)
        metadata = {
            "scope": json.dumps(plan["scope"], sort_keys=True),
            "artifact": "rc-audit",
        }
        with tempfile.TemporaryDirectory() as staging_dir:
            staging_path = Path(staging_dir)
            json_dir = staging_path / "artifacts" / "json"
            excel_dir = staging_path / "artifacts" / "excel"
            for _, path in outputs.items():
                destination_dir = json_dir
                suffix = path.suffix.lower()
                if suffix in {".xls", ".xlsx"}:
                    destination_dir = excel_dir
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / path.name
                destination.write_bytes(path.read_bytes())

            prefix_root = prefix.strip("/")
            if prefix_root:
                artifact_prefix_root = prefix_root
            else:
                artifact_prefix_root = "releasecopilot"

            if json_dir.exists() and any(json_dir.iterdir()):
                upload_directory(
                    bucket=bucket,
                    prefix="/".join([artifact_prefix_root, "artifacts", "json"]),
                    local_dir=json_dir,
                    subdir="audit",
                    region_name=options.region,
                    metadata=metadata,
                )
            if excel_dir.exists() and any(excel_dir.iterdir()):
                upload_directory(
                    bucket=bucket,
                    prefix="/".join([artifact_prefix_root, "artifacts", "excel"]),
                    local_dir=excel_dir,
                    subdir="audit",
                    region_name=options.region,
                    metadata=metadata,
                )
        uploaded = True
        LOGGER.info(
            "Uploaded audit artifacts",
            extra={"bucket": bucket, "prefix": prefix, "region": options.region},
        )

    LOGGER.info(
        "Offline audit completed",
        extra={"outputs": {k: str(v) for k, v in outputs.items()}},
    )
    return AuditResult(plan=plan, outputs=outputs, uploaded=uploaded)


__all__ = [
    "AuditInputError",
    "AuditOptions",
    "AuditResult",
    "load_cached_payloads",
    "parse_s3_uri",
    "run_audit",
]
