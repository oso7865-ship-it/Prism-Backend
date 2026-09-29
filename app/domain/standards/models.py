from uuid import UUID

from sqlalchemy import CheckConstraint, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class StandardDocument(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "standard_documents"
    __table_args__ = (
        Index("ix_standard_repository", "workspace_id", "repository_connection_id"),
        CheckConstraint("current_version > 0", name="ck_standard_version"),
    )
    workspace_id: Mapped[UUID]
    repository_connection_id: Mapped[UUID]
    created_by: Mapped[UUID]
    current_version: Mapped[int]
    active: Mapped[bool] = mapped_column(server_default=text("true"))


class StandardVersion(EntityMixin, Base):
    __tablename__ = "standard_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_standard_revision"),
        Index("ix_standard_version_tenant", "workspace_id", "document_id"),
        CheckConstraint("version > 0", name="ck_standard_revision"),
        CheckConstraint("kind IN ('CONVENTION','STRUCTURE')", name="ck_standard_kind"),
    )
    workspace_id: Mapped[UUID]
    document_id: Mapped[UUID]
    version: Mapped[int]
    title: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String(64))
    config: Mapped[dict[str, object]] = mapped_column(JSONB)
    sections: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
