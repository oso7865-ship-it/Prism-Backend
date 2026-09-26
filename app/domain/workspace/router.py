from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.workspace.schema.request import (
    Accept,
    ChangeRole,
    CreateWorkspace,
    Invite,
    Transfer,
)
from app.domain.workspace.schema.response import (
    CreatedInvitationResponse,
    InvitationResponse,
    MemberResponse,
    Page,
    WorkspaceResponse,
)
from app.domain.workspace.service import WorkspaceService


def workspace_router(service: WorkspaceService, auth: AuthAPI) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["workspace"])
    principal = Depends(auth.require_principal)

    @router.post("/workspaces", status_code=201, response_model=WorkspaceResponse)
    async def create(body: CreateWorkspace, p: Annotated[CurrentPrincipal, principal]) -> object:
        return await service.create(p.user_id, body.name)

    @router.get("/workspaces", response_model=Page[WorkspaceResponse])
    async def listing(
        p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> object:
        rows = await service.list_workspaces(p.user_id, cursor)
        return {"items": rows[:50], "next_cursor": rows[49].id if len(rows) > 50 else None}

    @router.get("/workspaces/{wid}/members", response_model=Page[MemberResponse])
    async def members(
        wid: UUID, p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> object:
        rows = await service.members(p.user_id, wid, cursor)
        return {"items": rows[:50], "next_cursor": rows[49].user_id if len(rows) > 50 else None}

    @router.post(
        "/workspaces/{wid}/invitations", status_code=201, response_model=CreatedInvitationResponse
    )
    async def invite(wid: UUID, body: Invite, p: Annotated[CurrentPrincipal, principal]) -> object:
        result = await service.invite(p.user_id, wid, body.target_github_user_id, body.role)
        return {"invitation": result.invitation, "token": result.token}

    @router.get("/workspaces/{wid}/invitations", response_model=Page[InvitationResponse])
    async def invites(
        wid: UUID, p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> object:
        rows = await service.invitations(p.user_id, wid, cursor)
        return {"items": rows[:50], "next_cursor": rows[49].id if len(rows) > 50 else None}

    @router.delete("/workspaces/{wid}/invitations/{iid}", status_code=204)
    async def revoke(wid: UUID, iid: UUID, p: Annotated[CurrentPrincipal, principal]) -> Response:
        await service.revoke(p.user_id, wid, iid)
        return Response(status_code=204)

    @router.post("/invitations/accept", response_model=WorkspaceResponse)
    async def accept(body: Accept, p: Annotated[CurrentPrincipal, principal]) -> object:
        return await service.accept(p.user_id, body.token)

    @router.patch("/workspaces/{wid}/members/{uid}", response_model=MemberResponse)
    async def role(
        wid: UUID, uid: UUID, body: ChangeRole, p: Annotated[CurrentPrincipal, principal]
    ) -> object:
        return await service.change_role(p.user_id, wid, uid, body.role)

    @router.delete("/workspaces/{wid}/members/{uid}", status_code=204)
    async def remove(wid: UUID, uid: UUID, p: Annotated[CurrentPrincipal, principal]) -> Response:
        await service.remove(p.user_id, wid, uid)
        return Response(status_code=204)

    @router.post("/workspaces/{wid}/transfer-ownership", response_model=MemberResponse)
    async def transfer(
        wid: UUID, body: Transfer, p: Annotated[CurrentPrincipal, principal]
    ) -> object:
        return await service.transfer(p.user_id, wid, body.user_id)

    return router
