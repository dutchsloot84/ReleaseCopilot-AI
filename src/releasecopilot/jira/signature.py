"""HMAC signature validation utilities for Jira webhooks."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
from typing import Union

BytesLike = Union[bytes, bytearray, memoryview]


def _ensure_bytes(value: str | BytesLike) -> bytes:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value)
    return value.encode("utf-8")


def _decode_signature(value: str) -> bytes | None:
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return base64.b64decode(candidate, validate=True)
    except binascii.Error:
        pass
    try:
        return bytes.fromhex(candidate)
    except ValueError:
        return None


def verify_signature(
    *,
    secret: str | BytesLike | None,
    body: str | BytesLike,
    signature: str | None,
) -> bool:
    """Return ``True`` when ``signature`` matches the Atlassian webhook HMAC."""

    if not secret or not signature:
        return False
    secret_bytes = _ensure_bytes(secret)
    body_bytes = _ensure_bytes(body)
    provided = _decode_signature(signature)
    if provided is None:
        return False
    expected = hmac.new(secret_bytes, body_bytes, hashlib.sha256).digest()
    return hmac.compare_digest(provided, expected)


__all__ = ["verify_signature"]
