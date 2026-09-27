"""Allow a reserved verification call; historical results remain unchanged."""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_review_counts", "review_runs", type_="check")
    op.create_check_constraint(
        "ck_review_counts",
        "review_runs",
        "generation>=0 AND connection_generation>0 AND input_tokens>=0 "
        "AND output_tokens>=0 AND call_attempts BETWEEN 0 AND 2",
    )


def downgrade():
    # PostgreSQL rejects this atomically if two-call history exists. Never rewrite history.
    op.drop_constraint("ck_review_counts", "review_runs", type_="check")
    op.create_check_constraint(
        "ck_review_counts",
        "review_runs",
        "generation>=0 AND connection_generation>0 AND input_tokens>=0 "
        "AND output_tokens>=0 AND call_attempts BETWEEN 0 AND 1",
    )
