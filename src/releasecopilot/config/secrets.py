"""Helpers for loading configuration secrets from AWS Secrets Manager."""

from __future__ import annotations

from functools import lru_cache
import json
from typing import Any, Dict, Optional

try:  # pragma: no cover - boto3 optional at import time
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - boto3 may be unavailable during tests
    boto3 = None  # type: ignore[assignment]
    BotoCoreError = ClientError = Exception  # type: ignore[assignment]

from ..utils.logging import redact_items

SecretValue = Any


@lru_cache(maxsize=None)
def _client():  # pragma: no cover - exercised indirectly via get_secret
    if boto3 is None:
        raise RuntimeError("boto3 is required to load secrets")
    return boto3.client("secretsmanager")


@lru_cache(maxsize=None)
def get_secret(name: str) -> Optional[SecretValue]:
    """Return the decoded secret for ``name``.

    ``None`` is returned when the secret cannot be resolved. JSON payloads are
    parsed into dictionaries while plain strings are returned as-is.
    """

    if not name:
        raise ValueError("Secret name must be provided")

    try:
        client = _client()
    except Exception:
        return None

    try:
        response = client.get_secret_value(SecretId=name)
    except (ClientError, BotoCoreError):
        return None

    secret_string = response.get("SecretString")
    if secret_string is not None:
        return _decode_secret_string(secret_string)

    binary_secret = response.get("SecretBinary")
    if isinstance(binary_secret, (bytes, bytearray)):
        try:
            return _decode_secret_string(binary_secret.decode("utf-8"))
        except Exception:  # pragma: no cover - unexpected encoding issues
            return None

    return None


def _decode_secret_string(payload: str) -> SecretValue:
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return payload
    return data


def safe_log_kv(**items: Any) -> Dict[str, Any]:
    """Return a sanitized mapping suitable for structured logging."""

    return redact_items(items)


__all__ = ["get_secret", "safe_log_kv"]
