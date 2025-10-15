"""CLI entry point for releasecopilot-ai."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:  # pragma: no cover - best effort optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - ignore missing dependency
    load_dotenv = None


from clients.bitbucket_client import BitbucketClient
from clients.jira_client import JiraClient, compute_fix_version_window
from clients.jira_store import JiraIssueStore
from config.settings import load_settings
from exporters.excel_exporter import ExcelExporter
from exporters.json_exporter import JSONExporter
from processors.audit_processor import AuditProcessor
from releasecopilot import uploader
from releasecopilot.errors import ReleaseCopilotError
from releasecopilot.logging_config import configure_logging, get_logger

from src.cli.shared import (
    AuditConfig,
    finalize_run,
    handle_dry_run,
    parse_args,
)


def _load_local_dotenv() -> None:
    if load_dotenv is None:
        return

    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return

    try:  # pragma: no cover - defensive guard
        load_dotenv(dotenv_path=env_path)
    except Exception:
        pass


_load_local_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = BASE_DIR / "temp_data"


def run_audit(config: AuditConfig) -> Dict[str, Any]:
    logger = get_logger(__name__)

    overrides: Dict[str, Any] = {}
    if config.s3_bucket or config.s3_prefix:
        overrides.setdefault("storage", {}).setdefault("s3", {})
        if config.s3_bucket:
            overrides["storage"]["s3"]["bucket"] = config.s3_bucket
        if config.s3_prefix:
            overrides["storage"]["s3"]["prefix"] = config.s3_prefix

    settings = load_settings(overrides=overrides)
    region = settings.get("aws", {}).get("region")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    jira_store = build_jira_store(settings)
    bitbucket_client = build_bitbucket_client(settings)

    freeze_dt = parse_freeze_date(config.freeze_date)
    window = compute_fix_version_window(freeze_dt, config.window_days)

    branches = determine_branches(config, settings)
    repos = determine_repos(config, settings)

    logger.info(
        "Starting audit",
        extra={
            "fix_version": config.fix_version,
            "repos": repos,
            "branches": branches,
            "window": {
                "start": window["start"].isoformat(),
                "end": window["end"].isoformat(),
            },
        },
    )

    issues, jira_cache_path = jira_store.fetch_issues(
        fix_version=config.fix_version,
        use_cache=config.use_cache,
    )
    jira_output = DATA_DIR / "jira_issues.json"
    write_json(jira_output, {"fixVersion": config.fix_version, "issues": issues})

    commits, cache_keys = bitbucket_client.fetch_commits(
        repositories=repos,
        branches=branches,
        start=window["start"],
        end=window["end"],
        use_cache=config.use_cache,
    )
    commits_output = DATA_DIR / "bitbucket_commits.json"
    write_json(
        commits_output, {"repos": repos, "branches": branches, "commits": commits}
    )

    processor = AuditProcessor(issues=issues, commits=commits)
    audit_result = processor.process()

    audit_payload = {
        "summary": audit_result.summary,
        "stories_with_no_commits": audit_result.stories_with_no_commits,
        "orphan_commits": audit_result.orphan_commits,
        "commit_story_mapping": audit_result.commit_story_mapping,
    }

    json_exporter = JSONExporter(DATA_DIR)
    excel_exporter = ExcelExporter(DATA_DIR)

    json_path = json_exporter.export(audit_payload, f"{config.output_prefix}.json")
    excel_path = excel_exporter.export(audit_payload, f"{config.output_prefix}.xlsx")

    summary_path = DATA_DIR / "summary.json"
    write_json(summary_path, audit_result.summary)

    artifacts = {
        "jira_issues": str(jira_output),
        "bitbucket_commits": str(commits_output),
        "json_report": str(json_path),
        "excel_report": str(excel_path),
        "summary": str(summary_path),
    }

    report_files: List[Path] = [json_path, excel_path, summary_path]

    # Collect raw payload cache files for optional S3 upload
    raw_files: List[Path] = [jira_output, commits_output]
    raw_cache_sources: List[Path] = [path for path in [jira_cache_path] if path]
    raw_files.extend(raw_cache_sources)
    for cache_key in cache_keys:
        cache_file = bitbucket_client.get_last_cache_file(cache_key)
        if cache_file:
            raw_files.append(cache_file)

    upload_artifacts(
        config=config,
        settings=settings,
        reports=report_files,
        raw_files=raw_files,
        region=region,
    )

    logger.info("Audit finished", extra={"summary": audit_result.summary})
    return {"summary": audit_result.summary, "artifacts": artifacts}


def build_jira_client(settings: Dict[str, Any]) -> JiraClient:
    jira_cfg = settings.get("jira", {})

    base_url = jira_cfg.get("base_url")
    if not base_url:
        raise RuntimeError("Jira base URL is not configured")

    credentials = jira_cfg.get("credentials", {})
    token_expiry_raw = credentials.get("token_expiry")
    token_expiry = int(token_expiry_raw) if token_expiry_raw else None

    return JiraClient(
        base_url=base_url,
        client_id=credentials.get("client_id"),
        client_secret=credentials.get("client_secret"),
        access_token=credentials.get("access_token"),
        refresh_token=credentials.get("refresh_token"),
        token_expiry=token_expiry,
        cache_dir=TEMP_DIR / "jira",
    )


def build_jira_store(settings: Dict[str, Any]) -> JiraIssueStore:
    storage_cfg = settings.get("storage", {})
    table_name = storage_cfg.get("dynamodb", {}).get("jira_issue_table")
    if not table_name:
        raise RuntimeError("Jira issue DynamoDB table name is not configured")

    region = settings.get("aws", {}).get("region")
    return JiraIssueStore(table_name=table_name, region_name=region)


def build_bitbucket_client(settings: Dict[str, Any]) -> BitbucketClient:
    bitbucket_cfg = settings.get("bitbucket", {})

    workspace = bitbucket_cfg.get("workspace")
    if not workspace:
        raise RuntimeError("Bitbucket workspace is not configured")

    credentials = bitbucket_cfg.get("credentials", {})

    return BitbucketClient(
        workspace=workspace,
        username=credentials.get("username"),
        app_password=credentials.get("app_password"),
        access_token=credentials.get("access_token"),
        cache_dir=TEMP_DIR / "bitbucket",
    )


def determine_branches(config: AuditConfig, settings: Dict[str, Any]) -> List[str]:
    if config.develop_only:
        return ["develop"]
    if config.branches:
        return config.branches
    return settings.get("bitbucket", {}).get("default_branches", ["main"])


def determine_repos(config: AuditConfig, settings: Dict[str, Any]) -> List[str]:
    if config.repos:
        return config.repos
    return settings.get("bitbucket", {}).get("repositories", [])


def parse_freeze_date(raw: Optional[str]) -> datetime:
    if not raw:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.strptime(raw, "%Y-%m-%d")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def upload_artifacts(
    *,
    config: AuditConfig,
    settings: Dict[str, Any],
    reports: Iterable[Path],
    raw_files: Iterable[Path],
    region: Optional[str],
) -> None:
    logger = get_logger(__name__)
    bucket = (
        config.s3_bucket
        or settings.get("storage", {}).get("s3", {}).get("bucket")
        or os.getenv("ARTIFACTS_BUCKET")
    )
    if not bucket:
        logger.info("No S3 bucket configured; skipping artifact upload.")
        return

    prefix_root = (
        config.s3_prefix
        or settings.get("storage", {}).get("s3", {}).get("prefix")
        or os.getenv("ARTIFACTS_PREFIX")
        or "releasecopilot"
    )
    prefix_root = prefix_root.strip("/")
    if not prefix_root:
        prefix_root = "releasecopilot"

    timestamp_source = datetime.utcnow()
    timestamp = timestamp_source.strftime("%Y-%m-%d_%H%M%S")
    generated_at = timestamp_source.replace(microsecond=0).isoformat() + "Z"
    artifact_scope = list(filter(None, [config.fix_version, timestamp]))

    metadata = {
        "fix-version": config.fix_version,
        "generated-at": generated_at,
    }
    git_sha = _detect_git_sha()
    if git_sha:
        metadata["git-sha"] = git_sha

    staging_root = TEMP_DIR / "s3_staging" / timestamp
    json_dir = staging_root / "artifacts" / "json"
    excel_dir = staging_root / "artifacts" / "excel"
    temp_dir = staging_root / "temp_data"

    json_reports = [path for path in reports if Path(path).suffix.lower() == ".json"]
    excel_reports = [
        path for path in reports if Path(path).suffix.lower() in {".xls", ".xlsx"}
    ]
    other_reports = [
        path
        for path in reports
        if Path(path).suffix.lower() not in {".json", ".xls", ".xlsx"}
    ]
    if other_reports:
        logger.warning(
            "Unclassified report types detected; uploading under JSON prefix.",
            extra={"files": [str(path) for path in other_reports]},
        )
        json_reports.extend(other_reports)

    _stage_files(json_dir, json_reports)
    _stage_files(excel_dir, excel_reports)
    _stage_files(temp_dir, raw_files)

    client = uploader.build_s3_client(region_name=region)

    subdir = "/".join(artifact_scope)

    if json_dir.exists():
        uploader.upload_directory(
            bucket=bucket,
            prefix="/".join([prefix_root, "artifacts", "json"]),
            local_dir=json_dir,
            subdir=subdir,
            client=client,
            metadata=metadata,
        )
    if excel_dir.exists():
        uploader.upload_directory(
            bucket=bucket,
            prefix="/".join([prefix_root, "artifacts", "excel"]),
            local_dir=excel_dir,
            subdir=subdir,
            client=client,
            metadata=metadata,
        )
    if temp_dir.exists():
        uploader.upload_directory(
            bucket=bucket,
            prefix="/".join([prefix_root, "temp_data"]),
            local_dir=temp_dir,
            subdir=subdir,
            client=client,
            metadata=metadata,
        )


def _stage_files(target_dir: Path, sources: Iterable[Path]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    counters: Dict[str, int] = {}
    for source in sources:
        if not source:
            continue
        path = Path(source)
        if not path.exists() or not path.is_file():
            continue
        name = path.name
        if name in counters:
            counters[name] += 1
            stem = path.stem
            suffix = path.suffix
            name = f"{stem}_{counters[name]}{suffix}"
        else:
            counters[name] = 0
        destination = target_dir / name
        shutil.copy2(path, destination)


def _detect_git_sha() -> Optional[str]:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    sha = output.decode("utf-8").strip()
    return sha or None


def main(argv: Optional[Iterable[str]] = None) -> int:
    args, config = parse_args(argv)
    configure_logging(args.log_level)
    logger = get_logger(__name__)

    if getattr(args, "dry_run", False):
        logger.info("Dry run requested", extra={"fix_version": config.fix_version})
        handle_dry_run(config)
        return 0

    try:
        result = run_audit(config)
    except ReleaseCopilotError as exc:
        logger.error("Audit execution failed", extra=getattr(exc, "context", {}))
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    finalize_run(result, args)
    logger.info("Audit completed", extra={"fix_version": config.fix_version})
    return 0


if __name__ == "__main__":
    sys.exit(main())
