"""Register Bitbucket webhook endpoints for popular ASGI/WSGI frameworks."""

from __future__ import annotations

from typing import Any

from releasecopilot.ingest.bitbucket_webhooks import BitbucketWebhookHandler
from releasecopilot.ingest.storage import CommitStorage

__all__ = ["register_bitbucket_webhook"]


def _is_fastapi_app(app: Any) -> bool:
    return app.__class__.__module__.startswith("fastapi") and hasattr(app, "include_router")


def _is_flask_app(app: Any) -> bool:
    return app.__class__.__module__.startswith("flask") and hasattr(app, "register_blueprint")


def register_bitbucket_webhook(
    app: Any,
    *,
    storage: CommitStorage,
    secret: str | None = None,
) -> Any:
    """Attach a Bitbucket webhook endpoint to ``app``.

    The helper detects whether ``app`` is a FastAPI or Flask instance at runtime
    to avoid importing optional dependencies for unrelated deployments.
    """

    handler = BitbucketWebhookHandler(storage=storage, secret=secret)

    if _is_fastapi_app(app):
        from fastapi import APIRouter, Request
        from fastapi.responses import JSONResponse

        router = APIRouter()

        @router.post("/webhooks/bitbucket")
        async def bitbucket_webhook(request: Request):  # pragma: no cover - framework wiring
            payload = await request.json()
            status, body = handler.process(payload, headers=request.headers)
            return JSONResponse(content=body, status_code=status)

        app.include_router(router)
        return router

    if _is_flask_app(app):
        from flask import Blueprint, jsonify, request

        blueprint = Blueprint("bitbucket_webhook", __name__)

        @blueprint.route("/webhooks/bitbucket", methods=["POST"])
        def bitbucket_webhook():  # pragma: no cover - framework wiring
            payload = request.get_json(force=True, silent=True) or {}
            status, body = handler.process(payload, headers=request.headers)
            response = jsonify(body)
            response.status_code = status
            return response

        app.register_blueprint(blueprint)
        return blueprint

    raise TypeError("Unsupported application type for Bitbucket webhook registration")
