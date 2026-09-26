"""Run the real test suite and record native diagnostics without storing raw logs/secrets."""

import argparse
import ctypes
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def loaded():
    if sys.platform != "win32":
        return None
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    return bool(kernel.GetModuleHandleW("npggNT64.des"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args()
    if args.child:
        import pytest

        before = loaded()
        status = pytest.main(["-q", "-p", "no:cacheprovider"])
        print("PRISM_NATIVE " + json.dumps({"before": before, "after": loaded()}), flush=True)
        raise SystemExit(status)

    from dotenv import dotenv_values
    from sqlalchemy.engine import make_url

    config = dotenv_values(".env")
    raw = os.environ.get("TEST_DATABASE_URL") or config.get("TEST_DATABASE_URL")
    if not raw:
        raise SystemExit("TEST_DATABASE_URL is required; no production database fallback")
    url = make_url(raw)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        raise SystemExit("A dedicated PostgreSQL _test database is required")
    record = {"started_at": datetime.now(UTC).isoformat(), "status": "STARTED"}
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(record, file)
    env = {**os.environ, "TEST_DATABASE_URL": raw, "PYTHONUTF8": "1"}
    run = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "scripts.check_windows_regression",
            str(args.output),
            "--child",
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    combined = run.stdout + run.stderr
    markers = [
        line.removeprefix("PRISM_NATIVE ")
        for line in run.stdout.splitlines()
        if line.startswith("PRISM_NATIVE ")
    ]
    record.update(
        {
            "finished_at": datetime.now(UTC).isoformat(),
            "status": "FINISHED",
            "exit_code": run.returncode,
            "native_access_violations": combined.count("Windows fatal exception: access violation"),
            "module_observation": json.loads(markers[-1]) if markers else None,
            "test_summary": [
                line
                for line in run.stdout.splitlines()
                if " passed" in line or " failed" in line or " skipped" in line
            ][-3:],
            "scope": "dedicated test DB, full pytest; stdout/stderr held in memory only",
        }
    )
    args.output.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, ensure_ascii=False))
    raise SystemExit(run.returncode)
