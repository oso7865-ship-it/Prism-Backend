from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.review.feedback import list_feedback, save_feedback
from app.domain.review.models import ReviewRun
from app.domain.review.policy import issue_key
from app.domain.review.service import ReviewService
from app.domain.review.source_view import excerpt
from app.shared.config.settings import Settings
from app.shared.github.client import GitHubClient


class StartReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purpose: Literal["CODE", "SECURITY", "STANDARDS"] = "CODE"
    consent: Literal[True]
    rerun_of: UUID | None = None


class FeedbackBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["OPEN", "ACKNOWLEDGED", "PLANNED", "INTENDED", "FALSE_POSITIVE"]
    note: str = Field(default="", max_length=500)


def view(row: ReviewRun) -> dict[str, object]:
    result = {
        name: getattr(row, name)
        for name in (
            "id analysis_id head_sha model prompt_version policy_version generation status "
            "requested_by created_at started_at finished_at call_attempts"
            " input_tokens output_tokens "
            "usage_uncertain error_code result purpose mode standard_versions"
        ).split()
    }
    if row.result:
        result["result"] = {
            **row.result,
            **{
                name: [
                    {**item, "key": issue_key(item)}
                    for item in cast(list[dict[str, object]], row.result.get(name, []))
                ]
                for name in ("issues", "questions")
            },
        }
    return result


def review_router(
    engine: AsyncEngine | None, auth: AuthAPI, settings: Settings, github: GitHubClient
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/workspaces/{wid}", tags=["review"])
    principal = Depends(auth.require_principal)
    service = ReviewService(engine, settings)

    @router.get("/reviews/{rid}/feedback")
    async def feedback(
        wid: UUID, rid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        rows = await list_feedback(service.ready(), p.user_id, wid, rid)
        return {
            "items": [
                {"key": r.issue_key, "state": r.state, "note": r.note, "updated_at": r.updated_at}
                for r in rows
            ]
        }

    @router.put("/reviews/{rid}/feedback/{key}")
    async def update_feedback(
        wid: UUID,
        rid: UUID,
        key: str,
        body: FeedbackBody,
        p: Annotated[CurrentPrincipal, principal],
    ) -> dict[str, object]:
        row = await save_feedback(service.ready(), p.user_id, wid, rid, key, body.state, body.note)
        return {
            "key": row.issue_key,
            "state": row.state,
            "note": row.note,
            "updated_at": row.updated_at,
        }

    @router.get("/reviews/{rid}/source/{key}")
    async def source_excerpt(
        wid: UUID,
        rid: UUID,
        key: str,
        p: Annotated[CurrentPrincipal, principal],
        line: Annotated[int | None, Query(ge=1, le=200_000)] = None,
    ) -> dict[str, object]:
        return await excerpt(service.ready(), github, p.user_id, wid, rid, key, line)

    @router.get("/reviews/{rid}/source-files/{file_id}")
    async def source_file(
        wid: UUID,
        rid: UUID,
        file_id: str,
        p: Annotated[CurrentPrincipal, principal],
        line: Annotated[int, Query(ge=1, le=200_000)] = 1,
    ) -> dict[str, object]:
        return await excerpt(
            service.ready(), github, p.user_id, wid, rid, file_id, line, by_file=True
        )

    @router.post("/analyses/{aid}/reviews", status_code=202)
    async def start(
        wid: UUID, aid: UUID, body: StartReview, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return view(
            await service.start(p.user_id, wid, aid, body.consent, body.rerun_of, body.purpose)
        )

    @router.get("/analyses/{aid}/reviews")
    async def history(
        wid: UUID,
        aid: UUID,
        p: Annotated[CurrentPrincipal, principal],
        purpose: Literal["CODE", "SECURITY", "STANDARDS"] = "CODE",
    ) -> dict[str, object]:
        return {
            "items": [view(r) for r in await service.history(p.user_id, wid, aid, purpose)],
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
