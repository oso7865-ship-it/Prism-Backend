"""Exercise pg_dump/restore on a new synthetic schema in local prism_test only.

No development/production data is read or backed up. Raw DB errors stay in memory.
"""

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

CONTAINER = "prism-local-db-1"
DATABASE = "prism_test"
SCHEMA = "backup_drill_" + uuid4().hex


def command(program, *args, data=None):
    result = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, program, "-U", "prism", "-d", DATABASE, *args],
        input=data, capture_output=True, timeout=60,
    )
    if result.returncode:
        raise RuntimeError(f"{program} failed; raw database output suppressed")
    return result.stdout


def sql(statement):
    return command("psql", "-X", "-v", "ON_ERROR_STOP=1", "-At", data=statement.encode())


def main():
    assert DATABASE.endswith("_test")
    assert re.fullmatch(r"backup_drill_[0-9a-f]{32}", SCHEMA)
    report = Path("reports/2026-09-27_backup-restore.json")
    with report.open("x", encoding="utf-8") as output:
        output.write('{"status":"STARTED"}\n')
    created = False
    record = {"at": datetime.now(UTC).isoformat(), "database": DATABASE,
              "scope": "synthetic schema, constraints/indexes and Korean text; no application data"}
    try:
        assert sql("SELECT current_database();").strip() == b"prism_test"
        sql(f'CREATE SCHEMA "{SCHEMA}";')
        created = True
        sql(f'''CREATE TABLE "{SCHEMA}".probe (id int PRIMARY KEY, label text NOT NULL);
            CREATE UNIQUE INDEX probe_label ON "{SCHEMA}".probe(label);
            INSERT INTO "{SCHEMA}".probe VALUES (1, '복구 확인'), (2, 'synthetic only');''')
        before = sql(f'SELECT id,label FROM "{SCHEMA}".probe ORDER BY id;')
        archive = command("pg_dump", "-Fc", "--schema", SCHEMA, "--no-owner", "--no-acl")
        assert archive.startswith(b"PGDMP")
        sql(f'DROP SCHEMA "{SCHEMA}" CASCADE;')
        command("pg_restore", "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl", data=archive)
        after = sql(f'SELECT id,label FROM "{SCHEMA}".probe ORDER BY id;')
        indexes = int(sql(f"SELECT count(*) FROM pg_indexes WHERE schemaname='{SCHEMA}';"))
        assert before == after and indexes == 2
        record.update(status="PASS", rows=2, indexes=indexes, byte_exact=True,
                      archive_sha256=hashlib.sha256(archive).hexdigest(), archive_bytes=len(archive))
    finally:
        if created:
            sql(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE;')
            assert sql(f"SELECT count(*) FROM pg_namespace WHERE nspname='{SCHEMA}';").strip() == b"0"
        record["temporary_schema_removed"] = created
        report.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
