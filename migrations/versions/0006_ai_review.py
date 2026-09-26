"""Bounded manual AI review, no physical foreign keys."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE review_runs (\n\tworkspace_id UUID NOT NULL, \n\ta"
        "nalysis_id UUID NOT NULL, \n\tpr_id UUID NOT NULL, \n\trepositor"
        "y_connection_id UUID NOT NULL, \n\tconnection_generation INTEG"
        "ER NOT NULL, \n\trequested_by UUID NOT NULL, \n\thead_sha VARCHA"
        "R(40) NOT NULL, \n\tmodel VARCHAR(80) NOT NULL, \n\tprompt_versi"
        "on VARCHAR(32) NOT NULL, \n\tpolicy_version VARCHAR(32) NOT NU"
        "LL, \n\tgeneration INTEGER DEFAULT 0 NOT NULL, \n\texecution_key"
        " VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(16) DEFAULT 'PENDING"
        "' NOT NULL, \n\tconsented_at TIMESTAMP WITH TIME ZONE NOT NULL"
        ", \n\tstarted_at TIMESTAMP WITH TIME ZONE, \n\tfinished_at TIMES"
        "TAMP WITH TIME ZONE, \n\tcall_attempts INTEGER DEFAULT 0 NOT N"
        "ULL, \n\tinput_tokens INTEGER DEFAULT 0 NOT NULL, \n\toutput_tok"
        "ens INTEGER DEFAULT 0 NOT NULL, \n\tusage_uncertain BOOLEAN DE"
        "FAULT false NOT NULL, \n\terror_code VARCHAR(64), \n\tresult JSO"
        "NB, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZON"
        "E DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME Z"
        "ONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT"
        " uq_review_execution UNIQUE (execution_key), \n\tCONSTRAINT ck"
        "_review_status CHECK (status IN ('PENDING','RUNNING','COMPLE"
        "TED','FAILED','CANCELED')), \n\tCONSTRAINT ck_review_terminal "
        "CHECK ((status IN ('COMPLETED','FAILED','CANCELED'))=(finish"
        "ed_at IS NOT NULL)), \n\tCONSTRAINT ck_review_counts CHECK (ge"
        "neration>=0 AND connection_generation>0 AND input_tokens>=0 "
        "AND output_tokens>=0 AND call_attempts BETWEEN 0 AND 1), \n\tC"
        "ONSTRAINT ck_review_digest CHECK (head_sha ~ '^[0-9a-f]{40}$"
        "' AND execution_key ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT ck_rev"
        "iew_result CHECK (status<>'COMPLETED' OR result IS NOT NULL)"
        "\n)\n\n"
    )
    op.execute("CREATE INDEX ix_review_budget ON review_runs (workspace_id, created_at)")
    op.execute(
        "CREATE INDEX ix_review_history ON review_runs (workspace_id, analysis_id, created_at, id)"
    )


def downgrade():
    op.drop_table("review_runs")
