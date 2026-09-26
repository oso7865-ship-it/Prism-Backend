"""Read-only, tenant-authorized snapshot exported to the review domain."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analysis.models import Finding
from app.domain.analysis.service import authorized, error


@dataclass(frozen=True)
class ReviewSnapshot:
    id: UUID
    pr_id: UUID
    repository_id: UUID
    connection_generation: int
    base_sha: str
    head_sha: str
    findings: list[dict[str, object]]
    config_version_id: UUID


async def require_review_read(s: AsyncSession, uid: UUID, wid: UUID, aid: UUID) -> None:
    await authorized(s, uid, wid, aid)


async def review_snapshot(s: AsyncSession, uid: UUID, wid: UUID, aid: UUID) -> ReviewSnapshot:
    row = await authorized(s, uid, wid, aid, active=True)
    if row.status != "COMPLETED":
        raise error("ANALYSIS_NOT_COMPLETED")
    findings = list(
        (
            await s.scalars(
                select(Finding)
                .where(Finding.workspace_id == wid, Finding.analysis_id == aid)
                .order_by(Finding.fingerprint)
                .limit(1000)
            )
        ).all()
    )
    ranks = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}
    findings.sort(key=lambda f: ranks.get(f.severity, 4))
    safe: list[dict[str, object]] = [
        dict[str, object](
            rule_id=f.rule_id, severity=f.severity, language=f.language, message=f.sanitized_message
        )
        for f in findings
        if f.category != "SECURITY"
    ][:10]
    return ReviewSnapshot(
        row.id,
        row.pr_id,
        row.repository_connection_id,
        row.connection_generation,
        row.base_sha,
        row.head_sha,
        safe,
        row.config_version_id,
    )
