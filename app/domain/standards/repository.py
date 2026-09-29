from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.standards.models import StandardDocument, StandardVersion


async def document(s: AsyncSession, wid: UUID, repo: UUID, did: UUID) -> StandardDocument | None:
    row: StandardDocument | None = await s.scalar(
        select(StandardDocument).where(
            StandardDocument.workspace_id == wid,
            StandardDocument.repository_connection_id == repo,
            StandardDocument.id == did,
        )
    )

    return row


async def listing(
    s: AsyncSession, wid: UUID, repo: UUID
) -> list[tuple[StandardDocument, StandardVersion]]:
    rows = await s.execute(
        select(StandardDocument, StandardVersion)
        .join(
            StandardVersion,
            (StandardVersion.document_id == StandardDocument.id)
            & (StandardVersion.version == StandardDocument.current_version)
            & (StandardVersion.workspace_id == wid),
        )
        .where(
            StandardDocument.workspace_id == wid, StandardDocument.repository_connection_id == repo
        )
        .order_by(StandardDocument.created_at, StandardDocument.id)
    )
    return [(d, v) for d, v in rows]


async def versions(s: AsyncSession, wid: UUID, did: UUID) -> list[StandardVersion]:
    return list(
        (
            await s.scalars(
                select(StandardVersion)
                .where(StandardVersion.workspace_id == wid, StandardVersion.document_id == did)
                .order_by(StandardVersion.version.desc())
            )
        ).all()
    )


async def version(s: AsyncSession, wid: UUID, did: UUID, number: int) -> StandardVersion | None:
    row: StandardVersion | None = await s.scalar(
        select(StandardVersion).where(
            StandardVersion.workspace_id == wid,
            StandardVersion.document_id == did,
            StandardVersion.version == number,
        )
    )

    return row


async def count(s: AsyncSession, wid: UUID, repo: UUID) -> int:
    return (
        await s.scalar(
            select(func.count())
            .select_from(StandardDocument)
            .where(
                StandardDocument.workspace_id == wid,
                StandardDocument.repository_connection_id == repo,
            )
        )
    ) or 0


async def remove(s: AsyncSession, doc: StandardDocument) -> None:
    await s.execute(
        delete(StandardVersion).where(
            StandardVersion.workspace_id == doc.workspace_id, StandardVersion.document_id == doc.id
        )
    )
    await s.delete(doc)


async def snapshots(
    s: AsyncSession, wid: UUID, repo: UUID, ids: list[str] | None
) -> list[StandardVersion]:
    query = (
        select(StandardVersion)
        .join(
            StandardDocument,
            (StandardVersion.document_id == StandardDocument.id)
            & (StandardDocument.workspace_id == wid),
        )
        .where(
            StandardVersion.workspace_id == wid,
            StandardDocument.repository_connection_id == repo,
            StandardDocument.active.is_(True),
        )
    )
    if ids is None:
        query = query.where(StandardVersion.version == StandardDocument.current_version)
    else:
        query = query.where(StandardVersion.id.in_([UUID(v) for v in ids]))
    return list((await s.scalars(query.order_by(StandardVersion.id))).all())
