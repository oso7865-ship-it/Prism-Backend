from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class AnalysisRun(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        UniqueConstraint("execution_key", name="uq_analysis_execution"),
        Index("ix_analysis_workspace_pr", "workspace_id", "pr_id", "created_at", "id"),
        Index("ix_analysis_repository_status", "repository_connection_id", "status", "id"),
        Index("ix_analysis_config", "config_version_id"),
        Index(
            "ix_analysis_finished", "finished_at", postgresql_where=text("finished_at IS NOT NULL")
        ),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELED')",
            name="ck_analysis_status",
        ),
        CheckConstraint(
            "coverage_status IN ('FULL_SCOPE','PARTIAL','NONE')", name="ck_analysis_coverage"
        ),
        CheckConstraint(
            (
                "actor_type IN ('USER','SYSTEM') AND ((actor_type='USER')=(request"
                "ed_by IS NOT NULL))"
            ),
            name="ck_analysis_actor",
        ),
        CheckConstraint(
            "scope='PR_CHANGED_FILES' AND generation>=0 AND connection_generation>0",
            name="ck_analysis_scope",
        ),
        CheckConstraint(
            "(status IN ('COMPLETED','FAILED','CANCELED'))=(finished_at IS NOT NULL)",
            name="ck_analysis_terminal",
        ),
        CheckConstraint(
            "status<>'COMPLETED' OR coverage_status IS NOT NULL", name="ck_analysis_complete"
        ),
        CheckConstraint(
            (
                "total_files>=0 AND included_files>=0 AND excluded_files>=0 AND fa"
                "iled_files>=0 AND not_evaluated_rules>=0 AND finding_count>=0"
            ),
            name="ck_analysis_counts",
        ),
        CheckConstraint(
            (
                "base_sha ~ '^[0-9a-f]{40}$' AND head_sha ~ '^[0-9a-f]{40}$' AND ("
                "merge_base_sha IS NULL OR merge_base_sha ~ '^[0-9a-f]{40}$')"
            ),
            name="ck_analysis_sha",
        ),
        CheckConstraint(
            (
                "execution_key ~ '^[0-9a-f]{64}$' AND effective_config_digest ~ '^"
                "[0-9a-f]{64}$' AND analyzer_build_digest ~ '^[0-9a-f]{64}$'"
            ),
            name="ck_analysis_digest",
        ),
    )
    workspace_id: Mapped[UUID]
    repository_connection_id: Mapped[UUID]
    pr_id: Mapped[UUID]
    connection_generation: Mapped[int]
    actor_type: Mapped[str] = mapped_column(String(16), server_default=text("'USER'"))
    requested_by: Mapped[UUID | None]
    base_sha: Mapped[str] = mapped_column(String(40))
    head_sha: Mapped[str] = mapped_column(String(40))
    merge_base_sha: Mapped[str | None] = mapped_column(String(40))
    rule_set_version: Mapped[str] = mapped_column(String(64))
    config_version_id: Mapped[UUID]
    effective_config_digest: Mapped[str] = mapped_column(String(64))
    analyzer_build_digest: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(24), server_default=text("'PR_CHANGED_FILES'"))
    generation: Mapped[int] = mapped_column(server_default=text("0"))
    execution_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'PENDING'"))
    coverage_status: Mapped[str | None] = mapped_column(String(16))
    coverage_reason: Mapped[str | None] = mapped_column(String(64))
    total_files: Mapped[int] = mapped_column(server_default=text("0"))
    included_files: Mapped[int] = mapped_column(server_default=text("0"))
    excluded_files: Mapped[int] = mapped_column(server_default=text("0"))
    failed_files: Mapped[int] = mapped_column(server_default=text("0"))
    not_evaluated_rules: Mapped[int] = mapped_column(server_default=text("0"))
    finding_count: Mapped[int] = mapped_column(server_default=text("0"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))


class AnalysisFileResult(EntityMixin, Base):
    __tablename__ = "analysis_file_results"
    __table_args__ = (
        UniqueConstraint("analysis_id", "side", "path_digest", name="uq_analysis_file"),
        Index("ix_analysis_file_status", "workspace_id", "analysis_id", "status", "id"),
        CheckConstraint("side IN ('HEAD','BASE','FILE')", name="ck_analysis_file_side"),
        CheckConstraint(
            "language IN ('JAVA','JAVASCRIPT','TYPESCRIPT','PYTHON')",
            name="ck_analysis_file_language",
        ),
        CheckConstraint(
            (
                "status IN ('INCLUDED','EXCLUDED','SOURCE_UNAVAILABLE','PARSE_ERRO"
                "R','LIMIT_EXCEEDED')"
            ),
            name="ck_analysis_file_status",
        ),
        CheckConstraint(
            "octet_length(file_path) BETWEEN 1 AND 4096 AND path_digest ~ '^[0-9a-f]{64}$'",
            name="ck_analysis_file_path",
        ),
        CheckConstraint(
            "jsonb_typeof(rule_outcomes)='array' AND octet_length(rule_outcomes::text)<=65536",
            name="ck_analysis_file_outcomes",
        ),
    )
    workspace_id: Mapped[UUID]
    analysis_id: Mapped[UUID]
    file_path: Mapped[str] = mapped_column(Text)
    path_digest: Mapped[str] = mapped_column(String(64))
    side: Mapped[str] = mapped_column(String(8))
    language: Mapped[str | None] = mapped_column(String(16))
    source_sha: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    finding_limit_reached: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    rule_outcomes: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )


class Finding(EntityMixin, Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("analysis_id", "fingerprint", name="uq_finding_fingerprint"),
        Index("ix_finding_workspace_analysis", "workspace_id", "analysis_id", "id"),
        Index("ix_finding_severity", "analysis_id", "severity", "id"),
        CheckConstraint(
            (
                "category IN ('ARCHITECTURE','SECURITY','RELIABILITY','MAINTAINABI"
                "LITY','STYLE','PERFORMANCE')"
            ),
            name="ck_finding_category",
        ),
        CheckConstraint(
            (
                "severity IN ('INFO','WARNING','ERROR','CRITICAL') AND confidence "
                "IN ('HIGH','MEDIUM','LOW')"
            ),
            name="ck_finding_axes",
        ),
        CheckConstraint(
            "side IN ('HEAD','BASE','FILE') AND scope_location IN ('CHANGED','CONTEXT','FILE')",
            name="ck_finding_location",
        ),
        CheckConstraint(
            "language IN ('JAVA','JAVASCRIPT','TYPESCRIPT','PYTHON')", name="ck_finding_language"
        ),
        CheckConstraint(
            (
                "(start_line IS NULL AND end_line IS NULL) OR (start_line IS NOT N"
                "ULL AND end_line IS NOT NULL AND start_line>=1 AND end_line>=star"
                "t_line)"
            ),
            name="ck_finding_lines",
        ),
        CheckConstraint(
            "octet_length(file_path) BETWEEN 1 AND 4096 AND fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_finding_path",
        ),
    )
    workspace_id: Mapped[UUID]
    analysis_id: Mapped[UUID]
    rule_id: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[str] = mapped_column(String(8))
    language: Mapped[str | None] = mapped_column(String(16))
    file_path: Mapped[str] = mapped_column(Text)
    start_line: Mapped[int | None]
    end_line: Mapped[int | None]
    side: Mapped[str] = mapped_column(String(8))
    scope_location: Mapped[str] = mapped_column(String(8))
    message_code: Mapped[str] = mapped_column(String(64))
    sanitized_message: Mapped[str] = mapped_column(String(2000))
    fingerprint: Mapped[str] = mapped_column(String(64))
