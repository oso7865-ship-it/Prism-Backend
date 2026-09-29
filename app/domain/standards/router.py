from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.standards.index import DocumentInput, index_document
from app.domain.standards.service import StandardsService


class StateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool
    expected_version: int = Field(ge=1)


def standards_router(engine: AsyncEngine | None, auth: AuthAPI) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/workspaces/{wid}/repositories/{repo}/standards", tags=["standards"]
    )
    principal = Depends(auth.require_principal)
    service = StandardsService(engine)

    @router.get("")
    async def listing(
        wid: UUID, repo: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return {"items": await service.list_documents(p.user_id, wid, repo)}

    @router.post("/preview")
    async def preview(
        wid: UUID, repo: UUID, body: DocumentInput, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        # Same tenant authorization as reading documents, no external model or persistence.
        await service.list_documents(p.user_id, wid, repo)
        return {
            "sections": [
                {k: v for k, v in item.items() if k != "terms"}
                for item in index_document(body.content)
            ]
        }

    @router.post("", status_code=201)
    async def create(
        wid: UUID, repo: UUID, body: DocumentInput, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return await service.save(p.user_id, wid, repo, body)

    @router.put("/{did}")
    async def update(
        wid: UUID,
        repo: UUID,
        did: UUID,
        body: DocumentInput,
        p: Annotated[CurrentPrincipal, principal],
    ) -> dict[str, object]:
        return await service.save(p.user_id, wid, repo, body, did)

    @router.get("/{did}/versions")
    async def history(
        wid: UUID, repo: UUID, did: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return {"items": await service.history(p.user_id, wid, repo, did)}

    @router.get("/{did}/versions/{number}")
    async def detail(
        wid: UUID, repo: UUID, did: UUID, number: int, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return await service.get(p.user_id, wid, repo, did, number)

    @router.patch("/{did}")
    async def state(
        wid: UUID,
        repo: UUID,
        did: UUID,
        body: StateInput,
        p: Annotated[CurrentPrincipal, principal],
    ) -> dict[str, object]:
        await service.state(p.user_id, wid, repo, did, body.active, body.expected_version)
        return {"active": body.active}

    @router.delete("/{did}")
    async def remove(
        wid: UUID,
        repo: UUID,
        did: UUID,
        p: Annotated[CurrentPrincipal, principal],
        expected_version: Annotated[int, Query(ge=1)],
    ) -> dict[str, object]:
        await service.remove(p.user_id, wid, repo, did, expected_version)
        return {"deleted": True}

    return router
