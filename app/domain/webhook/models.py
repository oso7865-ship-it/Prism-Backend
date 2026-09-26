from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class WebhookDelivery(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("provider", "delivery_id", name="uq_webhook_delivery"),
        CheckConstraint("provider='GITHUB' AND installation_id>0", name="ck_webhook_provider"),
        CheckConstraint(
            "event IN ('pull_request','installation','installation_repositories')",
            name="ck_webhook_event",
        ),
        CheckConstraint(
            "github_repository_id>0 AND pr_number>0 AND connection_generation>0",
            name="ck_webhook_ids",
        ),
        CheckConstraint(
            "(workspace_id IS NULL AND repository_connection_id IS NULL "
            "AND connection_generation IS NULL) OR (workspace_id IS NOT NULL "
            "AND repository_connection_id IS NOT NULL AND connection_generation IS NOT NULL)",
            name="ck_webhook_mapping",
        ),
        CheckConstraint(
            "event<>'pull_request' OR (workspace_id IS NOT NULL "
            "AND github_repository_id IS NOT NULL AND pr_number IS NOT NULL)",
            name="ck_webhook_pr",
        ),
        CheckConstraint(
            "status IN ('PENDING','PROCESSING','PROCESSED','FAILED','CANCELED','IGNORED')",
            name="ck_webhook_status",
        ),
        CheckConstraint(
            "(status IN ('PROCESSED','FAILED','CANCELED','IGNORED')) = (processed_at IS NOT NULL)",
            name="ck_webhook_terminal",
        ),
        CheckConstraint(
            "body_digest ~ '^[0-9a-f]{64}$' AND jsonb_typeof(affected_repository_ids)='array'",
            name="ck_webhook_payload",
        ),
        Index(
            "ix_webhook_workspace_received",
            "workspace_id",
            text("received_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_webhook_installation_received",
            "installation_id",
            text("received_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_webhook_processed",
            "processed_at",
            postgresql_where=text("processed_at IS NOT NULL"),
        ),
    )
    provider: Mapped[str] = mapped_column(String(16), server_default=text("'GITHUB'"))
    delivery_id: Mapped[str] = mapped_column(String(128))
    event: Mapped[str] = mapped_column(String(64))
    action: Mapped[str | None] = mapped_column(String(64))
    installation_id: Mapped[int] = mapped_column(BigInteger)
    github_repository_id: Mapped[int | None] = mapped_column(BigInteger)
    pr_number: Mapped[int | None]
    workspace_id: Mapped[UUID | None]
    repository_connection_id: Mapped[UUID | None]
    connection_generation: Mapped[int | None]
    affected_repository_ids: Mapped[list[int]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    body_digest: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'PENDING'"))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
