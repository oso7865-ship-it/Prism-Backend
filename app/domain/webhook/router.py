from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.webhook.exceptions import WebhookRejected
from app.domain.webhook.service import receive
from app.domain.webhook.verifier import MAX_BODY, verify
from app.shared.config.settings import Settings


def webhook_router(engine: AsyncEngine | None, settings: Settings) -> APIRouter:
    router = APIRouter(tags=["webhook"])

    @router.post("/webhooks/github")
    async def github(request: Request) -> Response:
        if engine is None or not settings.github_webhook_secret:
            raise HTTPException(503, "WEBHOOK_NOT_CONFIGURED")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_BODY:
                raise HTTPException(413, "WEBHOOK_BODY_TOO_LARGE")
            data.extend(chunk)
        try:
            return await accept(request, bytes(data))
        except WebhookRejected as exc:
            statuses = {
                "WEBHOOK_BODY_TOO_LARGE": 413,
                "WEBHOOK_SIGNATURE_INVALID": 401,
                "WEBHOOK_DELIVERY_MISMATCH": 409,
            }
            raise HTTPException(statuses.get(exc.code, 422), exc.code) from None

    async def accept(request: Request, data: bytes) -> Response:
        assert engine is not None and settings.github_webhook_secret
        event = verify(
            bytes(data),
            request.headers.get("x-hub-signature-256", ""),
            settings.github_webhook_secret.get_secret_value(),
            request.headers.get("x-github-delivery", ""),
            request.headers.get("x-github-event", ""),
        )
        return Response(status_code=await receive(engine, event) if event else 204)

    return router
