from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.repository.api import RepositoryAccess
from app.domain.standards import repository as store
from app.domain.standards.index import DocumentInput, digest, index_document
from app.domain.standards.models import StandardDocument, StandardVersion
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException, ErrorKind


def error(code: str, message: str, kind: ErrorKind = ErrorKind.CONFLICT) -> AppException:
    return AppException(code, message, kind)


async def document(s: AsyncSession, wid: UUID, repo: UUID, did: UUID) -> StandardDocument:
    row = await store.document(s, wid, repo, did)
    if row is None:
        raise error("STANDARD_NOT_FOUND", "문서를 찾을 수 없어요.", ErrorKind.NOT_FOUND)
    return row


def view(doc: StandardDocument, version: StandardVersion, full: bool = False) -> dict[str, object]:
    result: dict[str, object] = {
        "id": doc.id,
        "version_id": version.id,
        "version": version.version,
        "current_version": doc.current_version,
        "active": doc.active,
        "title": version.title,
        "kind": version.kind,
        "created_at": version.created_at,
        "digest": version.digest,
        "section_count": len(version.sections),
        **version.config,
    }
    if full:
        result.update(
            content=version.content,
            sections=[{k: v for k, v in item.items() if k != "terms"} for item in version.sections],
        )
    return result


class StandardsService:
    def __init__(self, engine: AsyncEngine | None) -> None:
        self.engine = engine

    def ready(self) -> AsyncEngine:
        if self.engine is None:
            raise error("DATABASE_UNAVAILABLE", "연결을 확인해 주세요.", ErrorKind.UNAVAILABLE)
        return self.engine

    async def access(
        self, s: AsyncSession, uid: UUID, wid: UUID, repo: UUID, write: bool = False
    ) -> None:
        await WorkspaceAccess(s).require_permission(uid, wid, "owner" if write else "read")
        await RepositoryAccess(s).require(uid, wid, repo, active=write)

    async def list_documents(self, uid: UUID, wid: UUID, repo: UUID) -> list[dict[str, object]]:
        async with transaction(self.ready()) as s:
            await self.access(s, uid, wid, repo)
            rows = await store.listing(s, wid, repo)
            return [view(d, v) for d, v in rows]

    async def history(self, uid: UUID, wid: UUID, repo: UUID, did: UUID) -> list[dict[str, object]]:
        async with transaction(self.ready()) as s:
            await self.access(s, uid, wid, repo)
            doc = await document(s, wid, repo, did)
            versions = await store.versions(s, wid, did)
            return [view(doc, v) for v in versions]

    async def get(
        self, uid: UUID, wid: UUID, repo: UUID, did: UUID, number: int
    ) -> dict[str, object]:
        async with transaction(self.ready()) as s:
            await self.access(s, uid, wid, repo)
            doc = await document(s, wid, repo, did)
            version = await store.version(s, wid, did, number)
            if version is None:
                raise error(
                    "STANDARD_NOT_FOUND", "문서 버전을 찾을 수 없어요.", ErrorKind.NOT_FOUND
                )
            return view(doc, version, True)

    async def save(
        self, uid: UUID, wid: UUID, repo: UUID, body: DocumentInput, did: UUID | None = None
    ) -> dict[str, object]:
        async with transaction(self.ready()) as s:
            await self.access(s, uid, wid, repo, True)
            if did is None:
                count = await store.count(s, wid, repo)
                if (count or 0) >= 8:
                    raise error("STANDARD_LIMIT", "저장소에는 문서를 최대 8개 등록할 수 있어요.")
                if body.expected_version != 0:
                    raise error("STANDARD_CONFLICT", "문서 버전을 확인해 주세요.")
                doc = StandardDocument(
                    workspace_id=wid,
                    repository_connection_id=repo,
                    created_by=uid,
                    current_version=1,
                )
                s.add(doc)
                await s.flush()
            else:
                doc = await document(s, wid, repo, did)
                if body.expected_version != doc.current_version:
                    raise error(
                        "STANDARD_CONFLICT", "다른 곳에서 문서가 바뀌었어요. 다시 열어 주세요."
                    )
                if doc.current_version >= 20:
                    raise error("STANDARD_LIMIT", "문서당 최대 20개 버전을 보관할 수 있어요.")
                doc.current_version += 1
            version = StandardVersion(
                workspace_id=wid,
                document_id=doc.id,
                version=doc.current_version,
                title=body.title.strip(),
                kind=body.kind,
                content=body.content,
                digest=digest(body),
                sections=index_document(body.content),
                config=body.model_dump(exclude={"title", "kind", "content", "expected_version"}),
            )
            s.add(version)
            await s.flush()
            return view(doc, version, True)

    async def state(
        self, uid: UUID, wid: UUID, repo: UUID, did: UUID, active: bool, expected: int
    ) -> None:
        async with transaction(self.ready()) as s:
            await self.access(s, uid, wid, repo, True)
            doc = await document(s, wid, repo, did)
            if doc.current_version != expected:
                raise error("STANDARD_CONFLICT", "문서가 바뀌었어요. 다시 열어 주세요.")
            doc.active = active

    async def remove(self, uid: UUID, wid: UUID, repo: UUID, did: UUID, expected: int) -> None:
        async with transaction(self.ready()) as s:
            await self.access(s, uid, wid, repo, True)
            doc = await document(s, wid, repo, did)
            if doc.current_version != expected:
                raise error("STANDARD_CONFLICT", "문서가 바뀌었어요. 다시 열어 주세요.")
            await store.remove(s, doc)
