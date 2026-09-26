from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.repository.schema import RepositoryResponse
from app.domain.repository.service import RepositoryService


def repository_router(engine: AsyncEngine | None, auth: AuthAPI) -> APIRouter:
    router = APIRouter(prefix="/api/v1/workspaces/{wid}/repositories", tags=["repository"])
    principal = Depends(auth.require_principal)

    service = RepositoryService(engine)

    @router.get("")
    async def listing(
        wid: UUID, p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> dict[str, object]:
        rows = await service.listing(p.user_id, wid, cursor)
        return {
            "items": [RepositoryResponse.model_validate(row) for row in rows[:50]],
            "next_cursor": rows[49].id if len(rows) > 50 else None,
        }

    @router.delete("/{rid}", status_code=204)
    async def disconnect(
        wid: UUID, rid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> Response:
        await service.disconnect(p.user_id, wid, rid)
        return Response(status_code=204)

    return router
