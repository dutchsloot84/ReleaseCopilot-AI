from __future__ import annotations

import base64
import hashlib
import hmac

import pytest

from releasecopilot.jira.signature import verify_signature


@pytest.mark.parametrize("secret", ["topsecret", b"topsecret"])
def test_verify_signature_accepts_valid_payload(secret):
    body = b'{"hello": "world"}'
    digest = hmac.new(
        secret if isinstance(secret, bytes) else secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(digest).decode("ascii")

    assert verify_signature(secret=secret, body=body, signature=signature) is True


@pytest.mark.parametrize(
    "signature",
    [None, "", "not-base64", base64.b64encode(b"wrong").decode("ascii")],
)
def test_verify_signature_rejects_invalid_payload(signature):
    secret = "another"
    body = b"{}"
    assert verify_signature(secret=secret, body=body, signature=signature) is False
