from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.repository.schema import (
    AppStatus,
    CandidateListResponse,
    CandidateResponse,
    ConnectStart,
    SelectRequest,
    SelectResponse,
)
from app.shared.config.settings import Settings
from app.shared.exception.base import AppException
from app.workflows.connect_repository import ConnectRepository

COOKIE = "prism_install_binding"


def github_router(flow: ConnectRepository, auth: AuthAPI, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["github-app"])
    principal = Depends(auth.require_principal)

    def installation_url() -> str | None:
        if not settings.github_app_ready:
            return None
        return f"https://github.com/apps/{settings.github_app_slug}/installations/new"

    @router.get("/github-app", response_model=AppStatus)
    async def status(p: Annotated[CurrentPrincipal, principal]) -> AppStatus:
        return AppStatus(configured=settings.github_app_ready, installation_url=installation_url())

    @router.post("/workspaces/{wid}/repositories/connect", response_model=ConnectStart)
    async def start(
        wid: UUID,
        response: Response,
        p: Annotated[CurrentPrincipal, principal],
    ) -> ConnectStart:
        url, binding = await flow.start(p.user_id, wid)
        response.set_cookie(
            COOKIE,
            binding,
            max_age=600,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/",
        )
        return ConnectStart(authorization_url=url)

    @router.get("/workspaces/{wid}/repositories/candidates", response_model=CandidateListResponse)
    async def candidates(
        wid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> CandidateListResponse:
        view = await flow.candidates(p.user_id, wid)
        return CandidateListResponse(
            items=[
                CandidateResponse(
                    github_repository_id=item.github_repository_id,
                    owner_login=item.owner_login,
                    repository_name=item.repository_name,
                    is_private=item.is_private,
                    state=state,
                )
                for item, state in view.items
            ],
            truncated=view.truncated,
            skipped_installations=view.skipped_installations,
            expires_at=view.expires_at,
            installation_url=installation_url(),
        )

    @router.post("/workspaces/{wid}/repositories/connect-selected", response_model=SelectResponse)
    async def connect_selected(
        wid: UUID, body: SelectRequest, p: Annotated[CurrentPrincipal, principal]
    ) -> SelectResponse:
        return SelectResponse(
            results=await flow.connect_selected(p.user_id, wid, body.github_repository_ids)
        )

    @router.get("/github-app/callback")
    async def callback(request: Request) -> Response:
        result = "choose"
        workspace: UUID | None = None
        try:
            if request.query_params.get("error"):
                result = "cancelled"
            else:
                workspace = await flow.callback(
                    request.query_params.get("code", ""),
                    request.query_params.get("state", ""),
                    request.cookies.get(COOKIE, ""),
                )
        except (AppException, TimeoutError):
            result = "failed"
        target = "/?repository_result=" + result
        if workspace:
            target += "&team=" + str(workspace)
        response = RedirectResponse(settings.public_app_origin + target, 302)
        response.delete_cookie(
            COOKIE, path="/", httponly=True, secure=settings.secure_cookies, samesite="lax"
        )
        return response

    return router
