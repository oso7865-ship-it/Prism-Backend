from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.repository.schema import AppStatus, ConnectRequest, ConnectStart
from app.shared.config.settings import Settings
from app.shared.exception.base import AppException
from app.workflows.connect_repository import ConnectRepository

COOKIE = "prism_install_binding"


def github_router(flow: ConnectRepository, auth: AuthAPI, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["github-app"])
    principal = Depends(auth.require_principal)

    @router.get("/github-app", response_model=AppStatus)
    async def status(p: Annotated[CurrentPrincipal, principal]) -> AppStatus:
        return AppStatus(
            configured=settings.github_app_ready,
            installation_url=f"https://github.com/apps/{settings.github_app_slug}/installations/new"
            if settings.github_app_ready
            else None,
        )

    @router.post("/workspaces/{wid}/repositories/connect", response_model=ConnectStart)
    async def start(
        wid: UUID,
        body: ConnectRequest,
        response: Response,
        p: Annotated[CurrentPrincipal, principal],
    ) -> ConnectStart:
        url, binding = await flow.start(p.user_id, wid, body.full_name)
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

    @router.get("/github-app/callback")
    async def callback(request: Request) -> Response:
        result = "connected"
        try:
            if request.query_params.get("error"):
                result = "cancelled"
            else:
                await flow.callback(
                    request.query_params.get("code", ""),
                    request.query_params.get("state", ""),
                    request.cookies.get(COOKIE, ""),
                )
        except (AppException, TimeoutError):
            result = "failed"
        response = RedirectResponse(
            settings.public_app_origin + "/?repository_result=" + result, 302
        )
        response.delete_cookie(
            COOKIE, path="/", httponly=True, secure=settings.secure_cookies, samesite="lax"
        )
        return response

    return router
