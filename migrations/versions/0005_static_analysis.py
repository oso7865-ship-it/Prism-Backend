"""Immutable analysis snapshots and source-free results; no physical foreign keys."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "CREATE TABLE analysis_runs (\n\tworkspace_id UUID NOT NULL, \n\trepos"
        "itory_connection_id UUID NOT NULL, \n\tpr_id UUID NOT NULL, \n\tconne"
        "ction_generation INTEGER NOT NULL, \n\tactor_type VARCHAR(16) DEFAU"
        "LT 'USER' NOT NULL, \n\trequested_by UUID, \n\tbase_sha VARCHAR(40) N"
        "OT NULL, \n\thead_sha VARCHAR(40) NOT NULL, \n\tmerge_base_sha VARCHA"
        "R(40), \n\trule_set_version VARCHAR(64) NOT NULL, \n\tconfig_version_"
        "id UUID NOT NULL, \n\teffective_config_digest VARCHAR(64) NOT NULL,"
        " \n\tanalyzer_build_digest VARCHAR(64) NOT NULL, \n\tscope VARCHAR(24"
        ") DEFAULT 'PR_CHANGED_FILES' NOT NULL, \n\tgeneration INTEGER DEFAU"
        "LT 0 NOT NULL, \n\texecution_key VARCHAR(64) NOT NULL, \n\tstatus VAR"
        "CHAR(16) DEFAULT 'PENDING' NOT NULL, \n\tcoverage_status VARCHAR(16"
        "), \n\tcoverage_reason VARCHAR(64), \n\ttotal_files INTEGER DEFAULT 0"
        " NOT NULL, \n\tincluded_files INTEGER DEFAULT 0 NOT NULL, \n\texclude"
        "d_files INTEGER DEFAULT 0 NOT NULL, \n\tfailed_files INTEGER DEFAUL"
        "T 0 NOT NULL, \n\tnot_evaluated_rules INTEGER DEFAULT 0 NOT NULL, \n"
        "\tfinding_count INTEGER DEFAULT 0 NOT NULL, \n\tstarted_at TIMESTAMP"
        " WITH TIME ZONE, \n\tfinished_at TIMESTAMP WITH TIME ZONE, \n\terror_"
        "code VARCHAR(64), \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH"
        " TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TI"
        "ME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT "
        "uq_analysis_execution UNIQUE (execution_key), \n\tCONSTRAINT ck_ana"
        "lysis_status CHECK (status IN ('PENDING','RUNNING','COMPLETED','F"
        "AILED','CANCELED')), \n\tCONSTRAINT ck_analysis_coverage CHECK (cov"
        "erage_status IN ('FULL_SCOPE','PARTIAL','NONE')), \n\tCONSTRAINT ck"
        "_analysis_actor CHECK (actor_type IN ('USER','SYSTEM') AND ((acto"
        "r_type='USER')=(requested_by IS NOT NULL))), \n\tCONSTRAINT ck_anal"
        "ysis_scope CHECK (scope='PR_CHANGED_FILES' AND generation>=0 AND "
        "connection_generation>0), \n\tCONSTRAINT ck_analysis_terminal CHECK"
        " ((status IN ('COMPLETED','FAILED','CANCELED'))=(finished_at IS N"
        "OT NULL)), \n\tCONSTRAINT ck_analysis_complete CHECK (status<>'COMP"
        "LETED' OR coverage_status IS NOT NULL), \n\tCONSTRAINT ck_analysis_"
        "counts CHECK (total_files>=0 AND included_files>=0 AND excluded_f"
        "iles>=0 AND failed_files>=0 AND not_evaluated_rules>=0 AND findin"
        "g_count>=0), \n\tCONSTRAINT ck_analysis_sha CHECK (base_sha ~ '^[0-"
        "9a-f]{40}$' AND head_sha ~ '^[0-9a-f]{40}$' AND (merge_base_sha I"
        "S NULL OR merge_base_sha ~ '^[0-9a-f]{40}$')), \n\tCONSTRAINT ck_an"
        "alysis_digest CHECK (execution_key ~ '^[0-9a-f]{64}$' AND effecti"
        "ve_config_digest ~ '^[0-9a-f]{64}$' AND analyzer_build_digest ~ '"
        "^[0-9a-f]{64}$')\n)"
    )
    op.execute("CREATE INDEX ix_analysis_config ON analysis_runs (config_version_id)")
    op.execute(
        "CREATE INDEX ix_analysis_finished ON analysis_runs (finished_at) "
        "WHERE finished_at IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_analysis_repository_status ON analysis_runs (repo"
        "sitory_connection_id, status, id)"
    )
    op.execute(
        "CREATE INDEX ix_analysis_workspace_pr ON analysis_runs (workspace"
        "_id, pr_id, created_at, id)"
    )
    op.execute(
        "CREATE TABLE analysis_file_results (\n\tworkspace_id UUID NOT NULL,"
        " \n\tanalysis_id UUID NOT NULL, \n\tfile_path TEXT NOT NULL, \n\tpath_d"
        "igest VARCHAR(64) NOT NULL, \n\tside VARCHAR(8) NOT NULL, \n\tlanguag"
        "e VARCHAR(16), \n\tsource_sha VARCHAR(40), \n\tstatus VARCHAR(24) NOT"
        " NULL, \n\treason_code VARCHAR(64), \n\tfinding_limit_reached BOOLEAN"
        " DEFAULT false NOT NULL, \n\trule_outcomes JSONB DEFAULT '[]'::json"
        "b NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME "
        "ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_"
        "analysis_file UNIQUE (analysis_id, side, path_digest), \n\tCONSTRAI"
        "NT ck_analysis_file_side CHECK (side IN ('HEAD','BASE','FILE')), "
        "\n\tCONSTRAINT ck_analysis_file_language CHECK (language IN ('JAVA'"
        ",'JAVASCRIPT','TYPESCRIPT','PYTHON')), \n\tCONSTRAINT ck_analysis_f"
        "ile_status CHECK (status IN ('INCLUDED','EXCLUDED','SOURCE_UNAVAI"
        "LABLE','PARSE_ERROR','LIMIT_EXCEEDED')), \n\tCONSTRAINT ck_analysis"
        "_file_path CHECK (octet_length(file_path) BETWEEN 1 AND 4096 AND "
        "path_digest ~ '^[0-9a-f]{64}$'), \n\tCONSTRAINT ck_analysis_file_ou"
        "tcomes CHECK (jsonb_typeof(rule_outcomes)='array' AND octet_lengt"
        "h(rule_outcomes::text)<=65536)\n)"
    )
    op.execute(
        "CREATE INDEX ix_analysis_file_status ON analysis_file_results (wo"
        "rkspace_id, analysis_id, status, id)"
    )
    op.execute(
        "CREATE TABLE findings (\n\tworkspace_id UUID NOT NULL, \n\tanalysis_i"
        "d UUID NOT NULL, \n\trule_id VARCHAR(64) NOT NULL, \n\trule_version V"
        "ARCHAR(64) NOT NULL, \n\tcategory VARCHAR(24) NOT NULL, \n\tseverity "
        "VARCHAR(16) NOT NULL, \n\tconfidence VARCHAR(8) NOT NULL, \n\tlanguag"
        "e VARCHAR(16), \n\tfile_path TEXT NOT NULL, \n\tstart_line INTEGER, \n"
        "\tend_line INTEGER, \n\tside VARCHAR(8) NOT NULL, \n\tscope_location V"
        "ARCHAR(8) NOT NULL, \n\tmessage_code VARCHAR(64) NOT NULL, \n\tsaniti"
        "zed_message VARCHAR(2000) NOT NULL, \n\tfingerprint VARCHAR(64) NOT"
        " NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE "
        "DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_findi"
        "ng_fingerprint UNIQUE (analysis_id, fingerprint), \n\tCONSTRAINT ck"
        "_finding_category CHECK (category IN ('ARCHITECTURE','SECURITY','"
        "RELIABILITY','MAINTAINABILITY','STYLE','PERFORMANCE')), \n\tCONSTRA"
        "INT ck_finding_axes CHECK (severity IN ('INFO','WARNING','ERROR',"
        "'CRITICAL') AND confidence IN ('HIGH','MEDIUM','LOW')), \n\tCONSTRA"
        "INT ck_finding_location CHECK (side IN ('HEAD','BASE','FILE') AND"
        " scope_location IN ('CHANGED','CONTEXT','FILE')), \n\tCONSTRAINT ck"
        "_finding_language CHECK (language IN ('JAVA','JAVASCRIPT','TYPESC"
        "RIPT','PYTHON')), \n\tCONSTRAINT ck_finding_lines CHECK ((start_lin"
        "e IS NULL AND end_line IS NULL) OR (start_line IS NOT NULL AND en"
        "d_line IS NOT NULL AND start_line>=1 AND end_line>=start_line)), "
        "\n\tCONSTRAINT ck_finding_path CHECK (octet_length(file_path) BETWE"
        "EN 1 AND 4096 AND fingerprint ~ '^[0-9a-f]{64}$')\n)"
    )
    op.execute("CREATE INDEX ix_finding_severity ON findings (analysis_id, severity, id)")
    op.execute(
        "CREATE INDEX ix_finding_workspace_analysis ON findings (workspace_id, analysis_id, id)"
    )


def downgrade():
    op.drop_table("findings")
    op.drop_table("analysis_file_results")
    op.drop_table("analysis_runs")
