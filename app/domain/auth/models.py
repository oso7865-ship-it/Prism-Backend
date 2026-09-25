from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin


class LoginAttempt(EntityMixin, Base):
    __tablename__ = "login_attempts"
    __table_args__ = (
        UniqueConstraint("state_hash", name="uq_login_attempts_state_hash"),
        CheckConstraint(
            "purpose IN ('OAUTH_LOGIN', 'GITHUB_INSTALL')", name="ck_login_attempts_purpose"
        ),
        CheckConstraint("state_hash ~ '^[0-9a-f]{64}$'", name="ck_login_attempts_state_hash"),
        CheckConstraint(
            "browser_binding_hash ~ '^[0-9a-f]{64}$'",
            name="ck_login_attempts_browser_binding_hash",
        ),
        CheckConstraint("expires_at > created_at", name="ck_login_attempts_expiry"),
        CheckConstraint(
            "(purpose = 'OAUTH_LOGIN' AND user_id IS NULL AND workspace_id IS NULL) OR "
            "(purpose = 'GITHUB_INSTALL' AND user_id IS NOT NULL AND workspace_id IS NOT NULL)",
            name="ck_login_attempts_binding",
        ),
        Index("ix_login_attempts_expires_at", "expires_at"),
    )

    purpose: Mapped[str] = mapped_column(String(24))
    state_hash: Mapped[str] = mapped_column(String(64))
    browser_binding_hash: Mapped[str] = mapped_column(String(64))
    user_id: Mapped[UUID | None]
    workspace_id: Mapped[UUID | None]
    return_path: Mapped[str] = mapped_column(String(1024))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RefreshSession(EntityMixin, Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="ck_refresh_sessions_token_hash"),
        CheckConstraint("expires_at > created_at", name="ck_refresh_sessions_expiry"),
        CheckConstraint(
            "(rotated_at IS NULL) = (replaced_by_id IS NULL)",
            name="ck_refresh_sessions_rotation_pair",
        ),
        CheckConstraint(
            "replaced_by_id IS NULL OR replaced_by_id <> id",
            name="ck_refresh_sessions_no_self_replacement",
        ),
        CheckConstraint(
            "(revoked_at IS NULL) = (revoke_reason IS NULL)",
            name="ck_refresh_sessions_revocation_pair",
        ),
        Index(
            "uq_refresh_sessions_replaced_by_id",
            "replaced_by_id",
            unique=True,
            postgresql_where=text("replaced_by_id IS NOT NULL"),
        ),
        Index("ix_refresh_sessions_user_family", "user_id", "family_id"),
        Index("ix_refresh_sessions_expires_at", "expires_at"),
    )

    user_id: Mapped[UUID]
    token_hash: Mapped[str] = mapped_column(String(64))
    family_id: Mapped[UUID]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[UUID | None]
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(String(64))
