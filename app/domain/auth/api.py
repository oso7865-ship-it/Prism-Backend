from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Header

from app.domain.auth.exceptions import SessionExpired
from app.domain.auth.service import AuthService
from app.domain.user.api import UserSnapshot


@dataclass(frozen=True)
class CurrentPrincipal:
    user_id: UUID
    user: UserSnapshot


class AuthAPI:
    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def require_principal(
        self,
        authorization: Annotated[str | None, Header()] = None,
    ) -> CurrentPrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            raise SessionExpired()
        user = await self.service.current_user(authorization[7:])
        return CurrentPrincipal(user.id, user)
