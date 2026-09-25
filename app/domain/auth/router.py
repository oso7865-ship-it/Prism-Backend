from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.domain.auth.dto import SessionTokens
from app.domain.auth.exceptions import OriginRejected
from app.domain.auth.schema.response import SessionResponse
from app.domain.auth.service import AuthService
from app.shared.config.settings import Settings
from app.shared.exception.base import AppException, ErrorKind
from app.shared.exception.handlers import error_response

REFRESH_COOKIE = "prism_refresh"
BINDING_COOKIE = "prism_oauth_binding"


def set_refresh(response: Response, tokens: SessionTokens) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=max(0, int((tokens.expires_at - datetime.now(UTC)).total_seconds())),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )


def require_csrf(request: Request, settings: Settings) -> None:
    if (
        request.headers.get("origin") != settings.public_app_origin
        or request.headers.get("x-prism-csrf") != "1"
    ):
        raise OriginRejected()


def auth_router(service: AuthService, settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

    @router.get("/github/start")
    async def start(return_path: Annotated[str, Query(max_length=1024)] = "/") -> Response:
        attempt = await service.start(return_path)
        response = RedirectResponse(attempt.url, status_code=302)
        response.set_cookie(
            BINDING_COOKIE,
            attempt.binding,
            max_age=600,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/",
        )
        return response

    @router.get("/github/callback")
    async def callback(request: Request) -> Response:
        # Always redirect with a fixed generic error; never copy provider text/query values.
        try:
            if request.query_params.get("error"):
                response = RedirectResponse(
                    settings.public_app_origin + "/?auth_error=cancelled", 302
                )
            else:
                tokens = await service.callback(
                    request.query_params.get("code", ""),
                    request.query_params.get("state", ""),
                    request.cookies.get(BINDING_COOKIE, ""),
                )
                response = RedirectResponse(settings.public_app_origin + "/", 302)
                set_refresh(response, tokens)
        except AppException:
            response = RedirectResponse(settings.public_app_origin + "/?auth_error=failed", 302)
        response.delete_cookie(BINDING_COOKIE, path="/", httponly=True, samesite="lax")
        return response

    @router.post("/refresh", response_model=SessionResponse)
    async def refresh(request: Request, response: Response) -> SessionResponse | Response:
        require_csrf(request, settings)
        try:
            tokens = await service.refresh(request.cookies.get(REFRESH_COOKIE, ""))
        except AppException as error:
            if error.kind != ErrorKind.UNAUTHORIZED:
                raise
            denied = error_response(error.code, error.public_message, 401)
            denied.delete_cookie(REFRESH_COOKIE, path="/", httponly=True, samesite="lax")
            return denied
        set_refresh(response, tokens)
        return SessionResponse(access_token=tokens.access_token)

    @router.post("/logout", status_code=204)
    async def logout(request: Request) -> Response:
        require_csrf(request, settings)
        await service.logout(request.cookies.get(REFRESH_COOKIE, ""))
        response = Response(status_code=204)
        response.delete_cookie(REFRESH_COOKIE, path="/", httponly=True, samesite="lax")
        return response

    return router
