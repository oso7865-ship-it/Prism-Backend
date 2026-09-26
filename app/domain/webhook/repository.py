from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repository.api import RepositorySnapshot
from app.domain.webhook.models import WebhookDelivery
from app.domain.webhook.verifier import Event


async def by_delivery(s: AsyncSession, delivery_id: str) -> WebhookDelivery | None:
    return (
        await s.scalars(
            select(WebhookDelivery).where(
                WebhookDelivery.provider == "GITHUB", WebhookDelivery.delivery_id == delivery_id
            )
        )
    ).one_or_none()


async def get(s: AsyncSession, did: UUID, lock: bool = False) -> WebhookDelivery | None:
    q = select(WebhookDelivery).where(WebhookDelivery.id == did)
    if lock:
        q = q.with_for_update().execution_options(populate_existing=True)
    return (await s.scalars(q)).one_or_none()


async def add(
    s: AsyncSession, did: UUID, event: Event, repo: RepositorySnapshot | None
) -> UUID | None:
    return (
        await s.execute(
            insert(WebhookDelivery)
            .values(
                id=did,
                provider="GITHUB",
                delivery_id=event.delivery_id,
                event=event.event,
                action=event.action,
                installation_id=event.installation_id,
                github_repository_id=event.repository_id,
                pr_number=event.number,
                workspace_id=repo.workspace_id if repo else None,
                repository_connection_id=repo.id if repo else None,
                connection_generation=repo.connection_generation if repo else None,
                affected_repository_ids=event.affected,
                body_digest=event.digest,
            )
            .on_conflict_do_nothing(index_elements=["provider", "delivery_id"])
            .returning(WebhookDelivery.id)
        )
    ).scalar_one_or_none()
