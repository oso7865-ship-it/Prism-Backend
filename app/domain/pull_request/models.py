from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class PullRequest(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repository_connection_id", "pr_number", name="uq_pr_repository_number"),
        UniqueConstraint(
            "repository_connection_id", "github_pr_id", name="uq_pr_repository_github"
        ),
        Index(
            "ix_pr_workspace_repository_updated",
            "workspace_id",
            "repository_connection_id",
            text("github_updated_at DESC"),
            text("id DESC"),
        ),
        CheckConstraint(
            "github_pr_id>0 AND pr_number>0 AND synced_connection_generation>0", name="ck_pr_ids"
        ),
        CheckConstraint(
            "state IN ('OPEN','CLOSED') AND merge_status IN ('UNKNOWN','NOT_MERGED','MERGED')",
            name="ck_pr_state",
        ),
        CheckConstraint("changed_files_count>=0 AND commits_count>=0", name="ck_pr_counts"),
        CheckConstraint(
            "base_sha ~ '^([0-9a-f]{40}|[0-9a-f]{64})$' AND head_sha ~ "
            "'^([0-9a-f]{40}|[0-9a-f]{64})$'",
            name="ck_pr_shas",
        ),
    )
    workspace_id: Mapped[UUID]
    repository_connection_id: Mapped[UUID]
    github_pr_id: Mapped[int] = mapped_column(BigInteger)
    pr_number: Mapped[int]
    title: Mapped[str] = mapped_column(Text)
    author_github_user_id: Mapped[int | None] = mapped_column(BigInteger)
    author_login: Mapped[str | None] = mapped_column(String(255))
    state: Mapped[str] = mapped_column(String(16))
    merge_status: Mapped[str] = mapped_column(String(16), server_default=text("'UNKNOWN'"))
    is_draft: Mapped[bool] = mapped_column(Boolean)
    base_ref: Mapped[str | None] = mapped_column(String(1024))
    head_ref: Mapped[str | None] = mapped_column(String(1024))
    base_sha: Mapped[str | None] = mapped_column(String(64))
    head_sha: Mapped[str | None] = mapped_column(String(64))
    changed_files_count: Mapped[int | None]
    commits_count: Mapped[int | None]
    github_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    github_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    synced_connection_generation: Mapped[int]


class PullRequestSyncRun(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "pull_request_sync_runs"
    __table_args__ = (
        Index(
            "uq_sync_active_repository",
            "repository_connection_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING','RUNNING')"),
        ),
        Index(
            "ix_sync_workspace_repository_created",
            "workspace_id",
            "repository_connection_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index("ix_sync_finished", "finished_at", postgresql_where=text("finished_at IS NOT NULL")),
        CheckConstraint("connection_generation>0 AND fetched_count>=0", name="ck_sync_counts"),
        CheckConstraint(
            "(actor_type='USER' AND requested_by IS NOT NULL) OR (actor_type='SYSTEM' "
            "AND requested_by IS NULL)",
            name="ck_sync_actor",
        ),
        CheckConstraint(
            "(mode='SINGLE' AND requested_pr_number>0 AND request_cursor IS NULL) OR "
            "(mode='RECENT' AND requested_pr_number IS NULL AND request_cursor IS NULL) "
            "OR (mode='PAGE' AND requested_pr_number IS NULL AND request_cursor IS NOT "
            "NULL)",
            name="ck_sync_mode",
        ),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELED')", name="ck_sync_status"
        ),
        CheckConstraint(
            "(status IN ('COMPLETED','FAILED','CANCELED')) = (finished_at IS NOT NULL)",
            name="ck_sync_finished",
        ),
    )
    workspace_id: Mapped[UUID]
    repository_connection_id: Mapped[UUID]
    connection_generation: Mapped[int]
    actor_type: Mapped[str] = mapped_column(String(16))
    requested_by: Mapped[UUID | None]
    mode: Mapped[str] = mapped_column(String(16))
    requested_pr_number: Mapped[int | None]
    request_cursor: Mapped[str | None] = mapped_column(String(1024))
    next_cursor: Mapped[str | None] = mapped_column(String(1024))
    etag: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'PENDING'"))
    fetched_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
