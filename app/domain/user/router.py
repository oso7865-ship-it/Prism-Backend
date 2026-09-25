from fastapi import APIRouter, Depends

from app.domain.auth.api import AuthAPI, CurrentPrincipal
from app.domain.user.schema.response import UserResponse


def user_router(auth: AuthAPI) -> APIRouter:
    router = APIRouter(prefix="/api/v1/users", tags=["user"])

    @router.get("/me", response_model=UserResponse)
    async def me(principal: CurrentPrincipal = Depends(auth.require_principal)) -> UserResponse:
        return UserResponse.model_validate(principal.user)

    return router
