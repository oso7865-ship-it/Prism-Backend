from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.pull_request.query import PRService
from app.domain.pull_request.schema import PRResponse, SyncRequest, SyncResponse
from app.shared.github.client import GitHubClient


def pr_router(engine: AsyncEngine | None, auth: AuthAPI, github: GitHubClient) -> APIRouter:
    router = APIRouter(prefix="/api/v1/workspaces/{wid}", tags=["pull-request"])
    principal = Depends(auth.require_principal)
    service = PRService(engine, github)

    @router.post("/repositories/{rid}/syncs", status_code=202, response_model=SyncResponse)
    async def sync(
        wid: UUID, rid: UUID, body: SyncRequest, p: Annotated[CurrentPrincipal, principal]
    ) -> SyncResponse:
        return SyncResponse.model_validate(
            await service.sync(p.user_id, wid, rid, body.page, body.pr_number)
        )

    @router.get("/repositories/{rid}/syncs/{sid}", response_model=SyncResponse)
    async def sync_status(
        wid: UUID, rid: UUID, sid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> SyncResponse:
        return SyncResponse.model_validate(await service.status(p.user_id, wid, rid, sid))

    @router.get("/repositories/{rid}/pull-requests")
    async def listing(
        wid: UUID, rid: UUID, p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> dict[str, object]:
        rows = await service.listing(p.user_id, wid, rid, cursor)
        return {
            "items": [PRResponse.model_validate(row) for row in rows[:50]],
            "next_cursor": rows[49].id if len(rows) > 50 else None,
        }

    @router.get("/pull-requests/{pid}", response_model=PRResponse)
    async def detail(wid: UUID, pid: UUID, p: Annotated[CurrentPrincipal, principal]) -> PRResponse:
        return PRResponse.model_validate(await service.detail(p.user_id, wid, pid))

    @router.get("/pull-requests/{pid}/github-reviews")
    async def reviews(
        wid: UUID,
        pid: UUID,
        p: Annotated[CurrentPrincipal, principal],
        kind: Literal["reviews", "comments", "review_comments", "commits"] = "reviews",
        page: Annotated[int, Query(ge=1, le=10000)] = 1,
    ) -> dict[str, object]:
        rows = await service.reviews(p.user_id, wid, pid, kind, page)
        return {"items": rows, "next_cursor": str(page + 1) if len(rows) == 30 else None}

    return router
