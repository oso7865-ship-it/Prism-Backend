from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class Job(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_job_dedupe"),
        UniqueConstraint("kind", "aggregate_id", name="uq_job_aggregate"),
        Index("ix_job_ready", "available_at", "id", postgresql_where=text("state='READY'")),
        Index("ix_job_leased", "lease_until", "id", postgresql_where=text("state='LEASED'")),
        Index("ix_job_workspace_state", "workspace_id", "state", "created_at", "id"),
        Index(
            "ix_job_completed", "completed_at", postgresql_where=text("completed_at IS NOT NULL")
        ),
        CheckConstraint(
            "kind IN ('SYNC_PULL_REQUESTS','ANALYZE_PR','EXPLAIN_FINDINGS','PROCESS_WEBHOOK')",
            name="ck_job_kind",
        ),
        CheckConstraint(
            "state IN ('READY','LEASED','SUCCEEDED','DEAD','CANCELED')", name="ck_job_state"
        ),
        CheckConstraint(
            "attempts>=0 AND attempts<=max_attempts AND max_attempts>0 AND lease_generation>=0",
            name="ck_job_attempts",
        ),
        CheckConstraint(
            "(state='LEASED' AND lease_until IS NOT NULL AND claimed_by IS NOT NULL) OR "
            "(state<>'LEASED' AND lease_until IS NULL AND claimed_by IS NULL)",
            name="ck_job_lease",
        ),
        CheckConstraint(
            "(state IN ('SUCCEEDED','DEAD','CANCELED')) = (completed_at IS NOT NULL)",
            name="ck_job_completed",
        ),
        CheckConstraint(
            "workspace_id IS NOT NULL OR kind='PROCESS_WEBHOOK'", name="ck_job_workspace"
        ),
        CheckConstraint(
            "dedupe_key ~ '^[0-9a-f]{64}$' AND jsonb_typeof(attempt_history)='array'",
            name="ck_job_payload",
        ),
    )
    workspace_id: Mapped[UUID | None]
    kind: Mapped[str] = mapped_column(String(32))
    aggregate_id: Mapped[UUID]
    dedupe_key: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), server_default=text("'READY'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int]
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_generation: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    claimed_by: Mapped[str | None] = mapped_column(String(128))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    attempt_history: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
