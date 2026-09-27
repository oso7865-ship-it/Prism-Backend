"""Personal review decisions, logical references only."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE review_feedback (
            id UUID PRIMARY KEY, workspace_id UUID NOT NULL,
            review_id UUID NOT NULL, user_id UUID NOT NULL,
            issue_key VARCHAR(64) NOT NULL, state VARCHAR(20) NOT NULL,
            note VARCHAR(500) DEFAULT '' NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            CONSTRAINT uq_review_feedback UNIQUE (review_id, user_id, issue_key),
            CONSTRAINT ck_feedback_state CHECK
                (state IN ('OPEN','ACKNOWLEDGED','PLANNED','INTENDED','FALSE_POSITIVE')),
            CONSTRAINT ck_feedback_key CHECK (issue_key ~ '^[0-9a-f]{64}$')
        )
    """)
    op.execute(
        "CREATE INDEX ix_review_feedback_owner ON review_feedback "
        "(workspace_id, user_id, updated_at)"
    )


def downgrade():
    op.drop_table("review_feedback")
