from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class Workspace(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_workspaces_name_nonblank"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_workspaces_status"),
        Index(
            "ix_workspaces_creator_created", "created_by", text("created_at DESC"), text("id DESC")
        ),
    )

    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'ACTIVE'"))
    created_by: Mapped[UUID]


class WorkspaceMember(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_workspace_user"),
        CheckConstraint("role IN ('OWNER', 'ADMIN', 'MEMBER')", name="ck_workspace_members_role"),
        CheckConstraint(
            "status IN ('ACTIVE', 'LEFT', 'REMOVED')", name="ck_workspace_members_status"
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND ended_at IS NULL) OR "
            "(status IN ('LEFT', 'REMOVED') AND ended_at IS NOT NULL)",
            name="ck_workspace_members_ended_at",
        ),
        Index(
            "uq_workspace_members_active_owner",
            "workspace_id",
            unique=True,
            postgresql_where=text("role = 'OWNER' AND status = 'ACTIVE'"),
        ),
        Index("ix_workspace_members_user_status", "user_id", "status", "workspace_id"),
        Index("ix_workspace_members_workspace_status", "workspace_id", "status", "id"),
    )

    workspace_id: Mapped[UUID]
    user_id: Mapped[UUID]
    role: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'ACTIVE'"))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invitation(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "invitations"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
        CheckConstraint(
            "target_github_user_id > 0", name="ck_invitations_target_github_user_id_positive"
        ),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_invitations_token_hash"),
        CheckConstraint("role IN ('MEMBER', 'ADMIN')", name="ck_invitations_role"),
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED')", name="ck_invitations_status"
        ),
        CheckConstraint("expires_at > created_at", name="ck_invitations_expiry"),
        CheckConstraint(
            "(status = 'ACCEPTED' AND accepted_at IS NOT NULL AND accepted_by IS NOT NULL) OR "
            "(status <> 'ACCEPTED' AND accepted_at IS NULL AND accepted_by IS NULL)",
            name="ck_invitations_acceptance",
        ),
        CheckConstraint(
            "(status = 'REVOKED') = (revoked_at IS NOT NULL)", name="ck_invitations_revocation"
        ),
        Index(
            "uq_invitations_pending_target",
            "workspace_id",
            "target_github_user_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index(
            "ix_invitations_pending_expiry",
            "expires_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
    )

    workspace_id: Mapped[UUID]
    target_github_user_id: Mapped[int] = mapped_column(BigInteger)
    invited_by: Mapped[UUID]
    token_hash: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), server_default=text("'MEMBER'"))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'PENDING'"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_by: Mapped[UUID | None]
