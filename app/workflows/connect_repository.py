from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import InstallState
from app.domain.pull_request.api import request_sync
from app.domain.repository.api import RepositoryAccess
from app.domain.repository.github import verify
from app.domain.user.api import UserAPI
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.github.client import GitHubClient


class ConnectRepository:
    def __init__(self, engine: AsyncEngine | None, github: GitHubClient) -> None:
        self.engine = engine
        self.github = github

    def ready(self) -> AsyncEngine:
        self.github.ready()
        if not self.engine:
            raise AppException(
                "DATABASE_UNAVAILABLE", "데이터베이스 연결이 필요합니다.", ErrorKind.UNAVAILABLE
            )
        return self.engine

    async def start(self, uid: UUID, wid: UUID, target: str) -> tuple[str, str]:
        engine = self.ready()
        async with transaction(engine) as s:
            await WorkspaceAccess(s).require_permission(uid, wid, "manage")
        state, binding = await InstallState(engine).start(uid, wid, target)
        return self.github.authorization_url(state, binding), binding

    async def callback(self, code: str, state: str, binding: str) -> None:
        engine = self.ready()
        if not code or len(code) > 1024:
            raise AppException(
                "INVALID_CODE", "연결을 다시 시작해 주세요.", ErrorKind.INVALID_INPUT
            )
        attempt = await InstallState(engine).consume(state, binding)
        async with transaction(engine) as s:
            await WorkspaceAccess(s).require_permission(
                attempt.user_id, attempt.workspace_id, "manage"
            )
            user = await UserAPI(s).get_active_user(attempt.user_id)
        import asyncio

        async with asyncio.timeout(50):
            verified = await verify(self.github, code, binding, attempt.target, user.github_user_id)
        try:
            async with transaction(engine) as s:
                repo = await RepositoryAccess(s).connect(
                    attempt.user_id, attempt.workspace_id, verified
                )
                await request_sync(s, attempt.user_id, attempt.workspace_id, repo.id)
        except IntegrityError:
            raise AppException(
                "REPOSITORY_EXISTS", "이미 다른 팀에 연결된 저장소입니다.", ErrorKind.CONFLICT
            ) from None
