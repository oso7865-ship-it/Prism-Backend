from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.exceptions import LoginRejected
from app.domain.auth.models import LoginAttempt
from app.shared.database.engine import transaction
from app.shared.security.hashing import random_token, token_hash


@dataclass(frozen=True)
class InstallAttempt:
    user_id: UUID
    workspace_id: UUID
    target: str


class InstallState:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def start(self, uid: UUID, wid: UUID, target: str) -> tuple[str, str]:
        state, binding = random_token(), random_token()
        async with transaction(self.engine) as s:
            s.add(
                LoginAttempt(
                    purpose="GITHUB_INSTALL",
                    user_id=uid,
                    workspace_id=wid,
                    return_path=target,
                    state_hash=token_hash(state),
                    browser_binding_hash=token_hash(binding),
                    expires_at=datetime.now(UTC) + timedelta(minutes=10),
                )
            )
        return state, binding

    async def consume(self, state: str, binding: str) -> InstallAttempt:
        if len(state) != 43 or len(binding) != 43:
            raise LoginRejected()
        async with transaction(self.engine) as s:
            result = await s.execute(
                update(LoginAttempt)
                .where(
                    LoginAttempt.purpose == "GITHUB_INSTALL",
                    LoginAttempt.state_hash == token_hash(state),
                    LoginAttempt.browser_binding_hash == token_hash(binding),
                    LoginAttempt.consumed_at.is_(None),
                    LoginAttempt.expires_at > datetime.now(UTC),
                )
                .values(consumed_at=datetime.now(UTC))
                .returning(
                    LoginAttempt.user_id, LoginAttempt.workspace_id, LoginAttempt.return_path
                )
            )
            row = result.one_or_none()
            if not row:
                raise LoginRejected()
            return InstallAttempt(row[0], row[1], row[2])
