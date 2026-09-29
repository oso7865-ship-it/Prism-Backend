"""Purpose-separated reviews and private versioned team standards."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "standard_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("repository_connection_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("current_version > 0", name="ck_standard_version"),
    )
    op.create_index(
        "ix_standard_repository", "standard_documents", ["workspace_id", "repository_connection_id"]
    )
    op.create_table(
        "standard_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("config", JSONB(), nullable=False),
        sa.Column("sections", JSONB(), nullable=False),
        sa.UniqueConstraint("document_id", "version", name="uq_standard_revision"),
        sa.CheckConstraint("version > 0", name="ck_standard_revision"),
        sa.CheckConstraint("kind IN ('CONVENTION','STRUCTURE')", name="ck_standard_kind"),
    )
    op.create_index(
        "ix_standard_version_tenant", "standard_versions", ["workspace_id", "document_id"]
    )
    op.add_column(
        "review_runs", sa.Column("purpose", sa.String(16), nullable=False, server_default="CODE")
    )
    op.add_column(
        "review_runs",
        sa.Column(
            "standard_versions", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.create_check_constraint(
        "ck_review_purpose", "review_runs", "purpose IN ('CODE','SECURITY','STANDARDS')"
    )


def downgrade():
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM standard_documents) OR EXISTS "
            "(SELECT 1 FROM review_runs WHERE purpose <> 'CODE')"
        )
    ).scalar():
        raise RuntimeError("Export new documents/reviews before downgrade; refusing data loss")
    op.drop_constraint("ck_review_purpose", "review_runs", type_="check")
    op.drop_column("review_runs", "standard_versions")
    op.drop_column("review_runs", "purpose")
    op.drop_table("standard_versions")
    op.drop_table("standard_documents")
