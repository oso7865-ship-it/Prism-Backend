"""Junior/senior review mode on user profiles and review runs (additive, defaulted)."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("review_mode", sa.String(8), nullable=False, server_default=sa.text("'SENIOR'")),
    )
    op.create_check_constraint(
        "ck_users_review_mode", "users", "review_mode IN ('JUNIOR', 'SENIOR')"
    )
    op.add_column(
        "review_runs",
        sa.Column("mode", sa.String(8), nullable=False, server_default=sa.text("'SENIOR'")),
    )
    op.create_check_constraint("ck_review_mode", "review_runs", "mode IN ('JUNIOR','SENIOR')")


def downgrade():
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM users WHERE review_mode <> 'SENIOR') OR EXISTS "
            "(SELECT 1 FROM review_runs WHERE mode <> 'SENIOR')"
        )
    ).scalar():
        raise RuntimeError(
            "Export junior-mode preferences/reviews before downgrade; refusing data loss"
        )
    op.drop_constraint("ck_review_mode", "review_runs", type_="check")
    op.drop_column("review_runs", "mode")
    op.drop_constraint("ck_users_review_mode", "users", type_="check")
    op.drop_column("users", "review_mode")
