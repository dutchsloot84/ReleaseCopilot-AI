"""Logging utilities supporting safe handling of sensitive data."""

from __future__ import annotations

from typing import Any, Mapping

_SENSITIVE_KEYWORDS = (
    "token",
    "secret",
    "password",
    "oauth",
    "apikey",
    "api_key",
    "api-key",
)


def _contains_sensitive_keyword(value: str) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in _SENSITIVE_KEYWORDS)


def redact(key: str | None, value: Any, *, placeholder: str = "***") -> Any:
    """Redact ``value`` when ``key`` suggests sensitive content.

    The helper recurses into mappings to redact nested secrets while keeping
    structure intact. Non-sensitive data is returned unchanged.
    """

    if key and _contains_sensitive_keyword(str(key)):
        return placeholder

    if isinstance(value, Mapping):
        return {
            nested_key: redact(nested_key, nested_value, placeholder=placeholder)
            for nested_key, nested_value in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        redacted_items = [
            (redact(key, item, placeholder=placeholder) if isinstance(item, Mapping) else item)
            for item in value
        ]
        if isinstance(value, tuple):
            return tuple(redacted_items)
        if isinstance(value, set):
            return set(redacted_items)
        return redacted_items

    return value


def redact_items(items: Mapping[str, Any]) -> dict[str, Any]:
    """Return a new mapping with sensitive keys redacted."""

    return {key: redact(key, value) for key, value in items.items()}


__all__ = ["redact", "redact_items"]
