"""Short-lived repository candidate lists for choose-from-GitHub connection (additive)."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repository_candidate_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("skipped_installations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_candidate_workspace_user"),
        sa.CheckConstraint("expires_at > created_at", name="ck_candidate_expiry"),
        sa.CheckConstraint(
            "jsonb_typeof(items) = 'array' AND jsonb_array_length(items) <= 300",
            name="ck_candidate_items",
        ),
    )
    op.create_index("ix_candidate_expires_at", "repository_candidate_sets", ["expires_at"])


def downgrade():
    # Rows are temporary (15 minutes) lists, so dropping the table loses no durable data.
    op.drop_index("ix_candidate_expires_at", table_name="repository_candidate_sets")
    op.drop_table("repository_candidate_sets")
