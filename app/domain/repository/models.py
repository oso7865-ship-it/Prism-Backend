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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class RepositoryConnection(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "repository_connections"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "github_repository_id", name="uq_repository_workspace_github"
        ),
        Index(
            "uq_repository_active_github",
            "github_repository_id",
            unique=True,
            postgresql_where=text("status IN ('ACTIVE','SUSPENDED')"),
        ),
        Index("ix_repository_workspace_status", "workspace_id", "status", "id"),
        Index("ix_repository_installation_status", "installation_id", "status", "id"),
        Index("ix_repository_config", "current_config_version_id"),
        CheckConstraint(
            "github_repository_id > 0 AND installation_id > 0", name="ck_repository_github_ids"
        ),
        CheckConstraint(
            "status IN ('ACTIVE','SUSPENDED','DISCONNECTED')", name="ck_repository_status"
        ),
        CheckConstraint(
            "connection_generation > 0 AND ai_policy_version > 0", name="ck_repository_versions"
        ),
        CheckConstraint("ai_mode IN ('OFF','FINDINGS_ONLY')", name="ck_repository_ai_mode"),
        CheckConstraint(
            "(status = 'DISCONNECTED') = (disconnected_at IS NOT NULL)",
            name="ck_repository_disconnected",
        ),
    )
    workspace_id: Mapped[UUID]
    github_repository_id: Mapped[int] = mapped_column(BigInteger)
    installation_id: Mapped[int] = mapped_column(BigInteger)
    owner_login: Mapped[str] = mapped_column(String(255))
    repository_name: Mapped[str] = mapped_column(String(255))
    is_private: Mapped[bool] = mapped_column(Boolean)
    default_branch: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'ACTIVE'"))
    connection_generation: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    current_config_version_id: Mapped[UUID]
    auto_analysis_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    ai_mode: Mapped[str] = mapped_column(String(24), server_default=text("'OFF'"))
    ai_policy_version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    ai_policy_changed_by: Mapped[UUID | None]
    connected_by: Mapped[UUID]
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RuleConfigVersion(EntityMixin, Base):
    __tablename__ = "rule_config_versions"
    __table_args__ = (
        UniqueConstraint(
            "repository_connection_id", "version", name="uq_config_repository_version"
        ),
        Index(
            "ix_config_workspace_repository",
            "workspace_id",
            "repository_connection_id",
            text("version DESC"),
        ),
        CheckConstraint("version > 0 AND schema_version > 0", name="ck_config_version"),
        CheckConstraint(
            "jsonb_typeof(rules)='object' AND jsonb_typeof(layer_mappings)='object' AND "
            "jsonb_typeof(ignored_paths)='array'",
            name="ck_config_json",
        ),
        CheckConstraint("ai_mode IN ('OFF','FINDINGS_ONLY')", name="ck_config_ai_mode"),
        CheckConstraint("config_digest ~ '^[0-9a-f]{64}$'", name="ck_config_digest"),
    )
    workspace_id: Mapped[UUID]
    repository_connection_id: Mapped[UUID]
    version: Mapped[int]
    schema_version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    rules: Mapped[dict[str, object]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    layer_mappings: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    ignored_paths: Mapped[list[str]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    auto_analysis_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    ai_mode: Mapped[str] = mapped_column(String(24), server_default=text("'OFF'"))
    config_digest: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[UUID]
