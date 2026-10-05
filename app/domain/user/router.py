from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.user.api import UserAPI
from app.domain.user.schema.request import PreferencesRequest
from app.domain.user.schema.response import UserResponse
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind


def user_router(auth: AuthAPI, engine: AsyncEngine | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/users", tags=["user"])

    @router.get("/me", response_model=UserResponse)
    async def me(principal: CurrentPrincipal = Depends(auth.require_principal)) -> UserResponse:
        return UserResponse.model_validate(principal.user)

    @router.patch("/me/preferences", response_model=UserResponse)
    async def update_preferences(
        body: PreferencesRequest,
        principal: CurrentPrincipal = Depends(auth.require_principal),
    ) -> UserResponse:
        if engine is None:
            raise AppException(
                "DATABASE_UNAVAILABLE", "설정을 저장할 수 없어요.", ErrorKind.UNAVAILABLE
            )
        async with transaction(engine) as session:
            user = await UserAPI(session).set_review_mode(principal.user_id, body.review_mode)
        return UserResponse.model_validate(user)

    return router
