from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.review.models import ReviewRun
from app.domain.review.service import ReviewService
from app.shared.config.settings import Settings


class StartReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent: Literal[True]
    rerun_of: UUID | None = None


def view(row: ReviewRun) -> dict[str, object]:
    return {
        name: getattr(row, name)
        for name in (
            "id analysis_id head_sha model prompt_version policy_version generation status "
            "requested_by created_at started_at finished_at call_attempts"
            " input_tokens output_tokens "
            "usage_uncertain error_code result"
        ).split()
    }


def review_router(engine: AsyncEngine | None, auth: AuthAPI, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1/workspaces/{wid}", tags=["review"])
    principal = Depends(auth.require_principal)
    service = ReviewService(engine, settings)

    @router.post("/analyses/{aid}/reviews", status_code=202)
    async def start(
        wid: UUID, aid: UUID, body: StartReview, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return view(await service.start(p.user_id, wid, aid, body.consent, body.rerun_of))

    @router.get("/analyses/{aid}/reviews")
    async def history(
        wid: UUID, aid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return {
            "items": [view(r) for r in await service.history(p.user_id, wid, aid)],
            "enabled": settings.ai_enabled,
            "model": settings.deepseek_model,
            "daily_limit": settings.ai_daily_limit,
        }

    @router.get("/reviews/{rid}")
    async def detail(
        wid: UUID, rid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return view(await service.get(p.user_id, wid, rid))

    @router.post("/reviews/{rid}/cancel", status_code=202)
    async def cancel(
        wid: UUID, rid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return view(await service.cancel(p.user_id, wid, rid))

    return router
