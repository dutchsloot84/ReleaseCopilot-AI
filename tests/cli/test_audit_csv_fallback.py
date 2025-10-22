"""CLI integration tests for the CSV fallback flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pytest

from cli.shared import AuditConfig
from releasecopilot.entrypoints import audit as audit_module
from releasecopilot.errors import JiraJQLFailed


class _FailingIssueProvider:
    def fetch_issues(
        self,
        *,
        fix_version: str,
        use_cache: bool = False,
        fields: Iterable[str] | None = None,
    ) -> tuple[list[dict[str, Any]], Path | None]:
        del fix_version, use_cache, fields
        raise JiraJQLFailed("JQL failed", context={"status_code": 400})


class _StaticCommitProvider:
    def fetch_commits(
        self,
        *,
        repositories: Iterable[str],
        branches: Iterable[str],
        start: Any,
        end: Any,
        use_cache: bool = False,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        del repositories, branches, start, end, use_cache
        return [], []

    def get_last_cache_file(self, name: str) -> Path | None:  # noqa: D401
        del name
        return None


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_settings = {
        "aws": {"region": "us-west-2"},
        "bitbucket": {"repositories": ["repo"], "default_branches": ["main"]},
        "storage": {},
    }

    monkeypatch.setattr(
        audit_module,
        "load_settings",
        lambda overrides=None: fake_settings,
    )


def test_run_audit_uses_csv_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    csv_path = tmp_path / "fallback.csv"
    csv_path.write_text(
        "\n".join(["Issue key,Summary", "ABC-1,Captured from CSV"]),
        encoding="utf-8",
    )

    prompts = iter([str(csv_path)])
    messages: list[str] = []

    monkeypatch.setattr(audit_module, "DATA_DIR", tmp_path / "data", raising=False)
    monkeypatch.setattr(audit_module, "TEMP_DIR", tmp_path / "temp", raising=False)
    monkeypatch.setattr(audit_module, "_phoenix_timestamp", lambda: "2025-10-15T07:30:00-07:00")
    monkeypatch.setattr(audit_module.click, "prompt", lambda *_, **__: next(prompts))
    monkeypatch.setattr(audit_module.click, "echo", lambda message, **__: messages.append(message))

    captured_upload: dict[str, Any] = {}

    def _capture_upload(**kwargs: Any) -> None:
        captured_upload["raw_files"] = list(kwargs.get("raw_files", []))

    monkeypatch.setattr(audit_module, "upload_artifacts", _capture_upload)

    config = AuditConfig(fix_version="4.0.0")
    result = audit_module.run_audit(
        config,
        issue_provider=_FailingIssueProvider(),
        commit_provider=_StaticCommitProvider(),
    )

    assert result["summary"]["total_stories"] == 1
    assert messages == [f"[2025-10-15T07:30:00-07:00] Loading issues from CSV fallback: {csv_path}"]
    assert any(csv_path == Path(path) for path in captured_upload["raw_files"])


def test_csv_prompt_retries_on_invalid_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    csv_path = tmp_path / "fallback.csv"
    csv_path.write_text(
        "\n".join(["Issue key,Summary", "ABC-2,Retry success"]),
        encoding="utf-8",
    )

    prompts = iter([str(tmp_path / "missing.csv"), str(csv_path)])
    outputs: list[tuple[str, bool]] = []

    def _echo(message: str, **kwargs: Any) -> None:
        outputs.append((message, kwargs.get("err", False)))

    monkeypatch.setattr(audit_module, "DATA_DIR", tmp_path / "data", raising=False)
    monkeypatch.setattr(audit_module, "TEMP_DIR", tmp_path / "temp", raising=False)
    monkeypatch.setattr(audit_module, "_phoenix_timestamp", lambda: "2025-10-15T08:00:00-07:00")
    monkeypatch.setattr(audit_module.click, "prompt", lambda *_, **__: next(prompts))
    monkeypatch.setattr(audit_module.click, "echo", _echo)
    monkeypatch.setattr(audit_module, "upload_artifacts", lambda **kwargs: None)

    config = AuditConfig(fix_version="4.1.0")
    audit_module.run_audit(
        config,
        issue_provider=_FailingIssueProvider(),
        commit_provider=_StaticCommitProvider(),
    )

    assert outputs[0][1] is True
    assert "CSV file not found" in outputs[0][0]
    assert outputs[-1][0].startswith("[2025-10-15T08:00:00-07:00]")
