"""Lambda handler for ingesting Jira webhook events into DynamoDB."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import os
import time
from typing import Any, Dict, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from releasecopilot.jira.signature import verify_signature
from releasecopilot.jira.sync import phoenix_now, recompute_correlation
from releasecopilot.jira.webhook_parser import JiraWebhookEvent, normalize_payload
from releasecopilot.logging_config import configure_logging, get_logger

configure_logging()
LOGGER = get_logger(__name__)

TABLE_NAME = os.environ["TABLE_NAME"]
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WEBHOOK_SECRET_ARN = os.getenv("WEBHOOK_SECRET_ARN")
ALLOWED_EVENTS = {
    "jira:issue_created",
    "jira:issue_updated",
    "jira:issue_deleted",
}

_RETRYABLE_ERRORS = {
    "ProvisionedThroughputExceededException",
    "ThrottlingException",
    "RequestLimitExceeded",
    "InternalServerError",
    "TransactionInProgressException",
}


_DDB = boto3.resource("dynamodb")
_TABLE = _DDB.Table(TABLE_NAME)
_SECRETS = boto3.client("secretsmanager") if WEBHOOK_SECRET_ARN else None
_SECRET_CACHE: Optional[str] = None


def handler(
    event: Dict[str, Any], context: Any
) -> Dict[str, Any]:  # pragma: no cover - context unused
    """Entrypoint for API Gateway -> Lambda invocations."""

    LOGGER.debug("Received event", extra={"event": event})

    method = (event.get("httpMethod") or "").upper()
    if method != "POST":
        return _response(405, {"message": "Method Not Allowed"})

    raw_body = _raw_body(event)

    expected_secret = _resolve_secret()
    if expected_secret:
        signature = _header(event, "X-Atlassian-Webhook-Signature")
        if not verify_signature(secret=expected_secret, body=raw_body, signature=signature):
            LOGGER.warning("Webhook authentication failed")
            return _response(401, {"message": "Unauthorized"})

    try:
        payload = _parse_body(raw_body)
    except ValueError as exc:
        LOGGER.warning("Malformed webhook payload: %s", exc)
        return _response(400, {"message": "Invalid payload"})

    try:
        normalized = normalize_payload(payload)
    except ValueError as exc:
        LOGGER.warning("Malformed webhook payload: %s", exc)
        return _response(400, {"message": str(exc)})

    event_type = normalized.event_type
    if event_type not in ALLOWED_EVENTS:
        LOGGER.info("Ignoring unsupported webhook event", extra={"event_type": event_type})
        return _response(202, {"ignored": True})

    if event_type == "jira:issue_deleted":
        result = _handle_delete(normalized)
    else:
        result = _handle_upsert(normalized)

    correlation = {}
    if result.get("success"):
        correlation = recompute_correlation(events=[normalized])

    status = 202 if result.get("success") else result.get("status", 500)
    body = {
        "ok": result.get("success", False),
        "received_at": phoenix_now().isoformat(timespec="seconds"),
        "event_id": normalized.delivery_id,
        **{k: v for k, v in result.items() if k != "success"},
    }
    if correlation:
        body["correlation_artifact"] = correlation.get("artifact_path")
    return _response(status, body)


def _header(event: Dict[str, Any], key: str) -> Optional[str]:
    headers = event.get("headers") or {}
    for candidate, value in headers.items():
        if candidate.lower() == key.lower():
            return value
    return None


def _raw_body(event: Dict[str, Any]) -> bytes:
    raw_body = event.get("body") or b""
    if event.get("isBase64Encoded"):
        raw_body = base64.b64decode(raw_body)
    if isinstance(raw_body, bytes):
        return raw_body
    if isinstance(raw_body, str):
        return raw_body.encode("utf-8")
    return json.dumps(raw_body).encode("utf-8")


def _parse_body(raw_body: bytes) -> Dict[str, Any]:
    if not raw_body:
        return {}
    try:
        text = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid encoding") from exc
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON") from exc


def _resolve_secret() -> Optional[str]:
    global _SECRET_CACHE
    if WEBHOOK_SECRET:
        return WEBHOOK_SECRET
    if not WEBHOOK_SECRET_ARN or _SECRETS is None:
        return None
    if _SECRET_CACHE is not None:
        return _SECRET_CACHE
    try:
        response = _SECRETS.get_secret_value(SecretId=WEBHOOK_SECRET_ARN)
    except ClientError as exc:  # pragma: no cover - defensive path
        LOGGER.error("Failed to resolve webhook secret", extra={"error": str(exc)})
        return None
    secret_string = response.get("SecretString") or ""
    resolved = _extract_secret_string(secret_string)
    _SECRET_CACHE = resolved
    return resolved


def _extract_secret_string(secret_string: str) -> Optional[str]:
    if not secret_string:
        return None
    try:
        data = json.loads(secret_string)
    except json.JSONDecodeError:
        return secret_string
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for key in ("token", "secret", "value"):
            if isinstance(data.get(key), str):
                return data[key]
        for value in data.values():
            if isinstance(value, str):
                return value
    return None


def _handle_upsert(event: JiraWebhookEvent) -> Dict[str, Any]:
    issue = event.issue
    issue_key = event.issue_key
    if not issue_key:
        LOGGER.error("Webhook payload missing issue identifier", extra={"payload": event.payload})
        return {"success": False, "status": 400, "message": "Missing issue identifier"}

    issue_id = event.issue_id
    issue_fields = event.fields or {}
    updated_at = event.updated_at or _now_iso()
    fix_versions = [
        fv.get("name") for fv in issue_fields.get("fixVersions") or [] if fv.get("name")
    ]
    primary_fix_version = fix_versions[0] if fix_versions else "UNASSIGNED"
    status = (issue_fields.get("status") or {}).get("name", "UNKNOWN")
    assignee = (issue_fields.get("assignee") or {}).get("accountId") or (
        (issue_fields.get("assignee") or {}).get("displayName")
    )

    idempotency_key = _compute_idempotency_key(event, issue_key, updated_at)

    item = {
        "issue_key": issue_key,
        "updated_at": updated_at,
        "issue_id": issue_id,
        "project_key": (issue_fields.get("project") or {}).get("key"),
        "status": status,
        "assignee": assignee or "UNASSIGNED",
        "fix_version": primary_fix_version,
        "fix_versions": fix_versions,
        "received_at": _now_iso(),
        "issue": issue,
        "deleted": False,
        "last_event_type": event.event_type,
        "idempotency_key": idempotency_key,
    }

    try:
        _put_item_with_retry(item)
    except ClientError as exc:
        LOGGER.error(
            "Failed to persist Jira issue",
            extra={"issue_key": issue_key, "issue_id": issue_id, "error": str(exc)},
        )
        return {"success": False, "status": 500, "message": "Failed to persist issue"}

    LOGGER.info(
        "Persisted Jira issue",
        extra={
            "issue_key": issue_key,
            "issue_id": issue_id,
            "fix_version": primary_fix_version,
            "event_id": event.delivery_id,
        },
    )
    return {"success": True, "issue_key": issue_key, "issue_id": issue_id}


def _handle_delete(event: JiraWebhookEvent) -> Dict[str, Any]:
    issue_key = event.issue_key
    if not issue_key:
        LOGGER.error("Delete webhook missing issue id", extra={"payload": event.payload})
        return {"success": False, "status": 400, "message": "Missing issue identifier"}

    updated_at = event.timestamp or _now_iso()
    idempotency_key = _compute_idempotency_key(event, issue_key, updated_at)

    try:
        tombstoned = _mark_tombstone(event, issue_key, updated_at, idempotency_key)
    except ClientError as exc:
        LOGGER.error(
            "Failed to delete Jira issue",
            extra={"issue_key": issue_key, "error": str(exc)},
        )
        return {"success": False, "status": 500, "message": "Failed to delete issue"}

    LOGGER.info(
        "Deleted Jira issue",
        extra={"issue_key": issue_key, "tombstoned": tombstoned, "event_id": event.delivery_id},
    )
    return {"success": True, "issue_key": issue_key, "deleted": True}


def _put_item_with_retry(item: Dict[str, Any]) -> None:
    params: Dict[str, Any] = {
        "Item": item,
        "ConditionExpression": "attribute_not_exists(idempotency_key) OR idempotency_key = :id",  # noqa: E501
        "ExpressionAttributeValues": {":id": item["idempotency_key"]},
    }

    _execute_with_backoff(_TABLE.put_item, params)


def _mark_tombstone(
    event: JiraWebhookEvent,
    issue_key: str,
    updated_at: str,
    idempotency_key: str,
) -> bool:
    latest = _fetch_latest_issue_item(issue_key)
    now = _now_iso()

    if latest:
        sort_key = latest.get("updated_at") or updated_at
        key = {"issue_key": issue_key, "updated_at": sort_key}
        update_params = {
            "Key": key,
            "UpdateExpression": "SET deleted = :deleted, last_event_type = :event, received_at = :now, idempotency_key = :id",  # noqa: E501
            "ExpressionAttributeValues": {
                ":deleted": True,
                ":event": event.event_type,
                ":now": now,
                ":id": idempotency_key,
            },
        }
        _execute_with_backoff(_TABLE.update_item, update_params)
        return True

    issue_payload = event.issue or {}
    issue_fields = event.fields or {}
    fix_versions = [
        fv.get("name") for fv in issue_fields.get("fixVersions") or [] if fv.get("name")
    ]
    item = {
        "issue_key": issue_key,
        "updated_at": updated_at,
        "issue_id": event.issue_id,
        "project_key": (issue_fields.get("project") or {}).get("key"),
        "status": (issue_fields.get("status") or {}).get("name", "UNKNOWN"),
        "assignee": (issue_fields.get("assignee") or {}).get("accountId")
        or (issue_fields.get("assignee") or {}).get("displayName")
        or "UNASSIGNED",
        "fix_version": fix_versions[0] if fix_versions else "UNASSIGNED",
        "fix_versions": fix_versions,
        "received_at": now,
        "issue": issue_payload,
        "deleted": True,
        "last_event_type": event.event_type,
        "idempotency_key": idempotency_key,
    }
    _put_item_with_retry(item)
    return False


def _fetch_latest_issue_item(issue_key: str) -> Optional[Dict[str, Any]]:
    try:
        response = _TABLE.query(
            KeyConditionExpression=Key("issue_key").eq(issue_key),
            ScanIndexForward=False,
            Limit=1,
        )
    except ClientError:
        raise

    items = response.get("Items") or []
    if not items:
        return None
    return items[0]


def _compute_idempotency_key(event: JiraWebhookEvent, issue_key: str, updated_at: str) -> str:
    payload = event.payload
    for key in ("deliveryId", "delivery_id", "eventId", "event_id"):
        value = payload.get(key)
        if value:
            return str(value)
    changelog = event.changelog or {}
    if isinstance(changelog, dict):
        identifier = changelog.get("id")
        if identifier:
            return str(identifier)
    timestamp = payload.get("timestamp")
    if timestamp:
        return f"{issue_key}:{timestamp}"
    return f"{issue_key}:{updated_at}:{event.event_type}"


def _execute_with_backoff(action, params: Dict[str, Any]) -> None:
    max_attempts = int(os.getenv("RC_DDB_MAX_ATTEMPTS", "5"))
    base_delay = float(os.getenv("RC_DDB_BASE_DELAY", "0.5"))
    attempt = 1
    while True:
        try:
            action(**params)
            return
        except ClientError as exc:
            code = (exc.response.get("Error", {}) or {}).get("Code")
            if code == "ConditionalCheckFailedException":
                item = params.get("Item") or {}
                key = params.get("Key") or {}
                issue_key = item.get("issue_key") or key.get("issue_key")
                LOGGER.info("Skipping outdated webhook", extra={"issue_key": issue_key})
                return
            if code not in _RETRYABLE_ERRORS or attempt >= max_attempts:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            LOGGER.warning(
                "Retrying DynamoDB operation",
                extra={"attempt": attempt, "delay": round(delay, 2)},
            )
            time.sleep(delay)
            attempt += 1


def _normalize_timestamp(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return (
            datetime.fromtimestamp(raw / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        )
    text = str(raw)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return text


def _now_iso() -> str:
    return phoenix_now().isoformat(timespec="seconds")


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


__all__ = ["handler"]
