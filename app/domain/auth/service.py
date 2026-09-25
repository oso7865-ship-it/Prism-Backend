from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth import repository
from app.domain.auth.dto import LoginStart, SessionTokens
from app.domain.auth.exceptions import AuthUnavailable, LoginRejected, SessionExpired
from app.domain.auth.github import GitHubOAuth
from app.domain.auth.models import LoginAttempt, RefreshSession
from app.domain.user.api import UserAPI, UserSnapshot
from app.shared.config.settings import Settings
from app.shared.database.engine import transaction
from app.shared.security.hashing import random_token, token_hash
from app.shared.security.token_codec import decode_access, encode_access


class AuthService:
    def __init__(self, engine: AsyncEngine | None, settings: Settings, github: GitHubOAuth) -> None:
        self.engine = engine
        self.settings = settings
        self.github = github

    def require_ready(self) -> tuple[AsyncEngine, str]:
        if not self.settings.auth_ready or self.engine is None or not self.settings.jwt_signing_key:
            raise AuthUnavailable()
        return self.engine, self.settings.jwt_signing_key.get_secret_value()

    async def start(self, return_path: str) -> LoginStart:
        engine, _ = self.require_ready()
        if return_path != "/":
            raise LoginRejected()
        state, binding = random_token(), random_token()
        async with transaction(engine) as session:
            session.add(
                LoginAttempt(
                    purpose="OAUTH_LOGIN",
                    state_hash=token_hash(state),
                    browser_binding_hash=token_hash(binding),
                    return_path="/",
                    expires_at=datetime.now(UTC) + timedelta(minutes=10),
                )
            )
        return LoginStart(self.github.authorization_url(state, binding), binding)

    async def callback(self, code: str, state: str, binding: str) -> SessionTokens:
        engine, key = self.require_ready()
        if not code or len(code) > 1024 or len(state) != 43 or len(binding) != 43:
            raise LoginRejected()
        async with transaction(engine) as session:
            consumed = await repository.consume_login(
                session, token_hash(state), token_hash(binding), datetime.now(UTC)
            )
        if not consumed:
            raise LoginRejected()
        # The state is consumed even when the external exchange fails. No DB locks across HTTP.
        identity = await self.github.identity(code, binding)
        refresh = random_token()
        expires = datetime.now(UTC) + timedelta(days=7)
        async with transaction(engine) as session:
            user = await UserAPI(session).upsert_github_identity(identity)
            session.add(
                RefreshSession(
                    user_id=user.id,
                    token_hash=token_hash(refresh),
                    family_id=uuid4(),
                    expires_at=expires,
                )
            )
            access = encode_access(user.id, key)
        return SessionTokens(access, refresh, expires)

    async def refresh(self, raw: str) -> SessionTokens:
        engine, key = self.require_ready()
        if len(raw) != 43:
            raise SessionExpired()
        result: SessionTokens | None = None
        async with transaction(engine) as session:
            current = await repository.lock_refresh(session, token_hash(raw))
            now = datetime.now(UTC)
            if current is not None:
                if current.rotated_at is not None or current.revoked_at is not None:
                    await repository.revoke_family(session, current.family_id, now, "REUSE")
                elif current.expires_at > now:
                    user = await UserAPI(session).get_active_user(current.user_id)
                    replacement, replacement_id = random_token(), uuid4()
                    session.add(
                        RefreshSession(
                            id=replacement_id,
                            user_id=user.id,
                            token_hash=token_hash(replacement),
                            family_id=current.family_id,
                            expires_at=current.expires_at,
                        )
                    )
                    current.rotated_at, current.replaced_by_id = now, replacement_id
                    result = SessionTokens(
                        encode_access(user.id, key), replacement, current.expires_at
                    )
        # Reuse revocations must commit before this error is raised.
        if result is None:
            raise SessionExpired()
        return result

    async def logout(self, raw: str) -> None:
        engine, _ = self.require_ready()
        if len(raw) != 43:
            return
        async with transaction(engine) as session:
            current = await repository.lock_refresh(session, token_hash(raw))
            if current:
                await repository.revoke_family(
                    session, current.family_id, datetime.now(UTC), "LOGOUT"
                )

    async def current_user(self, access: str) -> UserSnapshot:
        engine, key = self.require_ready()
        try:
            user_id = decode_access(access, key)
        except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
            raise SessionExpired() from None
        async with transaction(engine) as session:
            return await UserAPI(session).get_active_user(user_id)
