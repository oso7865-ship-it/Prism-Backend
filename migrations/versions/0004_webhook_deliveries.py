"""webhook_deliveries"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_deliveries",
        sa.Column(
            "provider", sa.String(length=16), server_default=sa.text("'GITHUB'"), nullable=False
        ),
        sa.Column("delivery_id", sa.String(length=128), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("github_repository_id", sa.BigInteger(), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("repository_connection_id", sa.Uuid(), nullable=True),
        sa.Column("connection_generation", sa.Integer(), nullable=True),
        sa.Column(
            "affected_repository_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("body_digest", sa.String(length=64), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default=sa.text("'PENDING'"), nullable=False
        ),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status IN ('PROCESSED','FAILED','CANCELED','IGNORED')) = (processed_at IS NOT NULL)",
            name="ck_webhook_terminal",
        ),
        sa.CheckConstraint(
            "body_digest ~ '^[0-9a-f]{64}$' AND jsonb_typeof(affected_repository_ids)='array'",
            name="ck_webhook_payload",
        ),
        sa.CheckConstraint(
            "event IN ('pull_request','installation','installation_repositories')",
            name="ck_webhook_event",
        ),
        sa.CheckConstraint(
            "event<>'pull_request' OR (workspace_id IS NOT NULL "
            "AND github_repository_id IS NOT NULL AND pr_number IS NOT NULL)",
            name="ck_webhook_pr",
        ),
        sa.CheckConstraint("provider='GITHUB' AND installation_id>0", name="ck_webhook_provider"),
        sa.CheckConstraint(
            "status IN ('PENDING','PROCESSING','PROCESSED','FAILED','CANCELED','IGNORED')",
            name="ck_webhook_status",
        ),
        sa.CheckConstraint(
            "(workspace_id IS NULL AND repository_connection_id IS NULL "
            "AND connection_generation IS NULL) OR (workspace_id IS NOT NULL "
            "AND repository_connection_id IS NOT NULL AND connection_generation IS NOT NULL)",
            name="ck_webhook_mapping",
        ),
        sa.CheckConstraint(
            "github_repository_id>0 AND pr_number>0 AND connection_generation>0",
            name="ck_webhook_ids",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "delivery_id", name="uq_webhook_delivery"),
    )
    op.create_index(
        "ix_webhook_installation_received",
        "webhook_deliveries",
        ["installation_id", sa.literal_column("received_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_webhook_processed",
        "webhook_deliveries",
        ["processed_at"],
        unique=False,
        postgresql_where=sa.text("processed_at IS NOT NULL"),
    )
    op.create_index(
        "ix_webhook_workspace_received",
        "webhook_deliveries",
        ["workspace_id", sa.literal_column("received_at DESC"), sa.literal_column("id DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_workspace_received", table_name="webhook_deliveries")
    op.drop_index(
        "ix_webhook_processed",
        table_name="webhook_deliveries",
        postgresql_where=sa.text("processed_at IS NOT NULL"),
    )
    op.drop_index("ix_webhook_installation_received", table_name="webhook_deliveries")
    op.drop_table("webhook_deliveries")
