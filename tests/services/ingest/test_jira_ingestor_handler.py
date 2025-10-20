"""Exercise the Jira ingestor handler helpers without external services."""

from __future__ import annotations

import importlib
import json
import sys
import types
from typing import Any, Dict

import pytest


class _ParameterNotFound(Exception):
    """Stub exception to mimic boto3's ParameterNotFound."""


def _build_stub_boto3() -> types.SimpleNamespace:
    secrets_value = {
        "client_id": "id",
        "client_secret": "secret",
        "refresh_token": "token",
        "base_url": "https://example.invalid",
    }

    class SecretsClient:
        def get_secret_value(self, SecretId: str) -> Dict[str, str]:  # noqa: N802 (AWS casing)
            return {"SecretString": json.dumps(secrets_value)}

    class SSMClient:
        exceptions = types.SimpleNamespace(ParameterNotFound=_ParameterNotFound)

        def __init__(self) -> None:
            self.parameters: Dict[str, str] = {}

        def get_parameter(self, Name: str) -> Dict[str, Dict[str, str]]:  # noqa: N803
            raise self.exceptions.ParameterNotFound()

        def put_parameter(
            self,
            Name: str,
            Value: str,
            Type: str,
            Overwrite: bool,
        ) -> None:  # noqa: N803
            self.parameters[Name] = Value

    class S3Client:
        def __init__(self) -> None:
            self.put_calls: list[Dict[str, Any]] = []

        def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:  # noqa: N803
            self.put_calls.append({"Bucket": Bucket, "Key": Key, "Body": Body})

        def generate_presigned_url(self, *args: Any, **kwargs: Any) -> str:
            return "https://example.invalid/presigned"

    secrets_client = SecretsClient()
    ssm_client = SSMClient()
    s3_client = S3Client()

    def client(name: str) -> Any:
        if name == "secretsmanager":
            return secrets_client
        if name == "ssm":
            return ssm_client
        if name == "s3":
            return s3_client
        raise ValueError(name)

    return types.SimpleNamespace(client=client)


@pytest.fixture(autouse=True)
def _patch_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_BUCKET", "bucket")
    monkeypatch.setenv("JIRA_OAUTH_SECRET", "secret-arn")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    stub_stream = types.SimpleNamespace(to_markdown=lambda value: f"md:{value}")
    stub_jira_api = types.SimpleNamespace(
        discover_field_map=lambda base_url, token: {
            "acceptance_criteria": "ac",
            "deployment_notes": "dn",
        },
        get_all_comments_if_needed=lambda base_url, token, issue: issue.get("fields", {})
        .get("comment", {})
        .get("comments", []),
        refresh_access_token=lambda client_id, client_secret, refresh_token: "token",
        search_page=lambda *args, **kwargs: {"issues": []},
    )

    monkeypatch.setitem(sys.modules, "adf_md", stub_stream)
    monkeypatch.setitem(sys.modules, "jira_api", stub_jira_api)
    monkeypatch.setitem(sys.modules, "boto3", _build_stub_boto3())


def test_normalize_issue_builds_expected_payload() -> None:
    module = importlib.reload(importlib.import_module("services.ingest.jira_ingestor.handler"))

    issue = {
        "key": "ABC-1",
        "fields": {
            "summary": "Example",
            "description": {"type": "doc"},
            "comment": {"comments": [{"body": {"type": "doc"}, "created": "2024-01-01"}]},
            "issuelinks": [],
            "labels": [],
            "components": [],
            "fixVersions": [],
            "issuetype": {"name": "Story"},
            "status": {"name": "Done"},
            "project": {"key": "RC"},
            "reporter": {"displayName": "Reporter"},
            "assignee": {"displayName": "Assignee"},
            "created": "2024-01-01",
            "updated": "2024-01-02",
        },
    }

    normalized = module._normalize_issue(
        issue,
        {"acceptance_criteria": "ac", "deployment_notes": "dn"},
        "https://example.invalid",
    )

    assert normalized["key"] == "ABC-1"
    assert normalized["description"]["markdown"].startswith("md:")
    assert normalized["comments"][0]["markdown"].startswith("md:")
    assert normalized["links"] == []
    assert normalized["uri"] == "https://example.invalid/browse/ABC-1"
    assert normalized["source"] == "jira"
