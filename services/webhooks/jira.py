"""Register Jira webhook endpoints for ASGI/WSGI frameworks."""

from __future__ import annotations

import os
from typing import Any

from clients.secrets_manager import CredentialStore
from releasecopilot.jira import (
    normalize_payload,
    phoenix_now,
    recompute_correlation,
    verify_signature,
)
from releasecopilot.logging_config import get_logger
from services.jira_sync_webhook import handler as lambda_handler

LOGGER = get_logger(__name__)

__all__ = ["register_jira_webhook"]


def _is_fastapi_app(app: Any) -> bool:
    return app.__class__.__module__.startswith("fastapi") and hasattr(app, "include_router")


def _is_flask_app(app: Any) -> bool:
    return app.__class__.__module__.startswith("flask") and hasattr(app, "register_blueprint")


def _resolve_secret() -> str | None:
    store = CredentialStore()
    secret = store.get(
        "jira_webhook_secret",
        env_var="JIRA_WEBHOOK_SECRET",
        secret_id=os.getenv("JIRA_WEBHOOK_SECRET_ARN"),
        secret_key="jira_webhook_secret",
    )
    if isinstance(secret, str):
        return secret
    return None


def register_jira_webhook(app: Any) -> Any:
    if _is_fastapi_app(app):
        from fastapi import APIRouter, Header, HTTPException, Request
        from fastapi.responses import JSONResponse

        router = APIRouter()

        @router.post("/webhooks/jira")
        async def jira_webhook(
            request: Request,
            x_atlassian_webhook_signature: str = Header(None),
        ) -> Any:  # pragma: no cover - framework wiring
            raw_body = await request.body()
            secret = _resolve_secret()
            if secret and not verify_signature(
                secret=secret, body=raw_body, signature=x_atlassian_webhook_signature
            ):
                raise HTTPException(status_code=401, detail="invalid signature")

            payload = await request.json()
            try:
                normalized = normalize_payload(payload)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            LOGGER.info(
                "Processing Jira webhook delivery",
                extra={"issue_key": normalized.issue_key, "event_id": normalized.delivery_id},
            )

            if normalized.event_type == "jira:issue_deleted":
                result = lambda_handler._handle_delete(normalized)
            else:
                result = lambda_handler._handle_upsert(normalized)

            correlation = {}
            if result.get("success"):
                correlation = recompute_correlation(events=[normalized])

            phoenix_timestamp = phoenix_now().isoformat(timespec="seconds")
            body = {
                "status": "ok" if result.get("success") else "error",
                "issue_key": normalized.issue_key,
                "event_type": normalized.event_type,
                "received_at": phoenix_timestamp,
            }
            if correlation:
                body["correlation_artifact"] = correlation.get("artifact_path")
            return JSONResponse(content=body, status_code=202 if result.get("success") else 500)

        app.include_router(router)
        return router

    if _is_flask_app(app):
        from flask import Blueprint, jsonify, request

        blueprint = Blueprint("jira_webhook", __name__)

        @blueprint.route("/webhooks/jira", methods=["POST"])
        def jira_webhook() -> Any:  # pragma: no cover - framework wiring
            raw_body = request.get_data(cache=False)
            secret = _resolve_secret()
            if secret and not verify_signature(
                secret=secret,
                body=raw_body,
                signature=request.headers.get("X-Atlassian-Webhook-Signature"),
            ):
                return jsonify({"detail": "invalid signature"}), 401

            payload = request.get_json(force=True, silent=True) or {}
            try:
                normalized = normalize_payload(payload)
            except ValueError as exc:  # pragma: no cover - defensive
                return jsonify({"detail": str(exc)}), 400

            LOGGER.info(
                "Processing Jira webhook delivery",
                extra={"issue_key": normalized.issue_key, "event_id": normalized.delivery_id},
            )

            if normalized.event_type == "jira:issue_deleted":
                result = lambda_handler._handle_delete(normalized)
            else:
                result = lambda_handler._handle_upsert(normalized)

            correlation = {}
            if result.get("success"):
                correlation = recompute_correlation(events=[normalized])

            phoenix_timestamp = phoenix_now().isoformat(timespec="seconds")
            body = {
                "status": "ok" if result.get("success") else "error",
                "issue_key": normalized.issue_key,
                "event_type": normalized.event_type,
                "received_at": phoenix_timestamp,
            }
            if correlation:
                body["correlation_artifact"] = correlation.get("artifact_path")
            response = jsonify(body)
            response.status_code = 202 if result.get("success") else 500
            return response

        app.register_blueprint(blueprint)
        return blueprint

    raise TypeError("Unsupported application type for Jira webhook registration")
