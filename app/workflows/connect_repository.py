import asyncio
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.auth.api import InstallState
from app.domain.pull_request.api import request_sync
from app.domain.repository.api import (
    CandidateRepository,
    CandidateView,
    RepositoryAccess,
    VerifiedRepository,
)
from app.domain.repository.github import collect
from app.domain.repository.schema import SelectResult
from app.domain.user.api import UserAPI
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind
from app.shared.github.client import GitHubClient

# Marker stored with the one-time OAuth state: nothing user-supplied is part of the target.
TARGET = "repositories"


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

    async def start(self, uid: UUID, wid: UUID) -> tuple[str, str]:
        engine = self.ready()
        async with transaction(engine) as s:
            await WorkspaceAccess(s).require_permission(uid, wid, "manage")
        state, binding = await InstallState(engine).start(uid, wid, TARGET)
        return self.github.authorization_url(state, binding), binding

    async def callback(self, code: str, state: str, binding: str) -> UUID:
        """Fetch what the user may connect and keep it briefly. Nothing is connected here."""
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
        async with asyncio.timeout(50):
            found = await collect(self.github, code, binding, user.github_user_id)
        async with transaction(engine) as s:
            await RepositoryAccess(s).save_candidates(attempt.user_id, attempt.workspace_id, found)
        return attempt.workspace_id

    async def candidates(self, uid: UUID, wid: UUID) -> CandidateView:
        engine = self.ready()
        async with transaction(engine) as s:
            return await RepositoryAccess(s).candidates(uid, wid)

    async def connect_selected(self, uid: UUID, wid: UUID, ids: list[int]) -> list[SelectResult]:
        """Connect only the chosen repositories; one failure never blocks the others."""
        engine = self.ready()
        async with transaction(engine) as s:
            listed = await RepositoryAccess(s).candidate_map(uid, wid)
        results = [await self._connect_one(engine, uid, wid, gid, listed.get(gid)) for gid in ids]
        return results

    async def _connect_one(
        self,
        engine: AsyncEngine,
        uid: UUID,
        wid: UUID,
        gid: int,
        item: CandidateRepository | None,
    ) -> SelectResult:
        if item is None:
            return SelectResult(
                github_repository_id=gid,
                owner_login=None,
                repository_name=None,
                status="NOT_IN_LIST",
            )

        def result(status: str, repository_id: UUID | None = None) -> SelectResult:
            return SelectResult(
                github_repository_id=gid,
                owner_login=item.owner_login,
                repository_name=item.repository_name,
                status=status,
                repository_id=repository_id,
            )

        if not item.admin:
            return result("ADMIN_REQUIRED")
        verified = VerifiedRepository(
            item.github_repository_id,
            item.installation_id,
            item.owner_login,
            item.repository_name,
            item.is_private,
            item.default_branch,
        )
        try:
            async with transaction(engine) as s:
                repo = await RepositoryAccess(s).connect(uid, wid, verified)
                await request_sync(s, uid, wid, repo.id)
        except IntegrityError:
            return result("CONFLICT")
        except AppException as error:
            return result("ALREADY_CONNECTED" if error.code == "REPOSITORY_EXISTS" else "FAILED")
        return result("CONNECTED", repo.id)
