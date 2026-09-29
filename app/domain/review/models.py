from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class ReviewRun(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "review_runs"
    __table_args__ = (
        UniqueConstraint("execution_key", name="uq_review_execution"),
        Index("ix_review_history", "workspace_id", "analysis_id", "created_at", "id"),
        Index("ix_review_budget", "workspace_id", "created_at"),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELED')",
            name="ck_review_status",
        ),
        CheckConstraint(
            "(status IN ('COMPLETED','FAILED','CANCELED'))=(finished_at IS NOT NULL)",
            name="ck_review_terminal",
        ),
        CheckConstraint(
            "generation>=0 AND connection_generation>0 AND input_tokens>="
            "0 AND output_tokens>=0 AND call_attempts BETWEEN 0 AND 2",
            name="ck_review_counts",
        ),
        CheckConstraint(
            "head_sha ~ '^[0-9a-f]{40}$' AND execution_key ~ '^[0-9a-f]{64}$'",
            name="ck_review_digest",
        ),
        CheckConstraint("status<>'COMPLETED' OR result IS NOT NULL", name="ck_review_result"),
        CheckConstraint("purpose IN ('CODE','SECURITY','STANDARDS')", name="ck_review_purpose"),
    )
    purpose: Mapped[str] = mapped_column(String(16), server_default=text("'CODE'"))
    standard_versions: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    workspace_id: Mapped[UUID]
    analysis_id: Mapped[UUID]
    pr_id: Mapped[UUID]
    repository_connection_id: Mapped[UUID]
    connection_generation: Mapped[int]
    requested_by: Mapped[UUID]
    head_sha: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(32))
    policy_version: Mapped[str] = mapped_column(String(32))
    generation: Mapped[int] = mapped_column(server_default=text("0"))
    execution_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'PENDING'"))
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    call_attempts: Mapped[int] = mapped_column(server_default=text("0"))
    input_tokens: Mapped[int] = mapped_column(server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(server_default=text("0"))
    usage_uncertain: Mapped[bool] = mapped_column(server_default=text("false"))
    error_code: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class ReviewFeedback(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "review_feedback"
    __table_args__ = (
        UniqueConstraint("review_id", "user_id", "issue_key", name="uq_review_feedback"),
        Index("ix_review_feedback_owner", "workspace_id", "user_id", "updated_at"),
        CheckConstraint(
            "state IN ('OPEN','ACKNOWLEDGED','PLANNED','INTENDED','FALSE_POSITIVE')",
            name="ck_feedback_state",
        ),
        CheckConstraint("issue_key ~ '^[0-9a-f]{64}$'", name="ck_feedback_key"),
    )
    workspace_id: Mapped[UUID]
    review_id: Mapped[UUID]
    user_id: Mapped[UUID]
    issue_key: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(String(500), server_default=text("''"))
