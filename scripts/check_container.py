"""Offline, resource-bounded image smoke test. No credentials or source repos mounted."""

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

PROGRAM = r'''
import asyncio, json, os, time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.shared.config.settings import Settings
from app.domain.analysis.parser_process import parse_file
assert os.geteuid() != 0
assert not Path('/app/.env').exists()
assert not Path('/app/tests').exists()
samples = [('A.java', b'class A { int f() { return 1; } }'),
           ('a.py', b'def f():\n    return 1\n'),
           ('a.js', b'const x = 1;'), ('a.ts', b'const x: number = 1;')]
async def main():
    statuses=[]
    start=time.monotonic()
    for i in range(100):
        path, source=samples[i%4]
        result=await parse_file(path,source)
        statuses.append(result.status)
    timed=await parse_file('a.py', b'x=1', timeout=0.000001)
    assert timed.reason == 'PARSER_TIMEOUT'
    return statuses, time.monotonic()-start
statuses,elapsed=asyncio.run(main())
assert len(set(statuses)) == 1 and statuses[0] == 'INCLUDED', set(statuses)
with TestClient(create_app(Settings(_env_file=None))) as client:
    assert client.get('/health/live').status_code == 200
    assert client.get('/health/ready').status_code == 503
peak=Path('/sys/fs/cgroup/memory.peak')
print(json.dumps(dict(uid=os.geteuid(),files=100,languages=4,statuses=sorted(set(statuses)),
    elapsed_seconds=round(elapsed,3),parser_timeout='PASS',live=200,ready_without_db=503,
    cgroup_peak_bytes=int(peak.read_text()) if peak.exists() else None)))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/2026-09-27_container-smoke.json"))
    args = parser.parse_args()
    run = subprocess.run(
        ["docker", "run", "--rm", "-i", "--network", "none", "--memory", "512m", "--cpus", "1",
         "prism-predeploy:local", "python", "-"],
        input=PROGRAM, text=True, capture_output=True, timeout=120,
    )
    if run.returncode:
        print(run.stderr)
        raise SystemExit(run.returncode)
    result = {"at": datetime.now(UTC).isoformat(), "scope": "100 small synthetic files sequentially; not worst-case load",
              "network": "none", "memory_limit_mb": 512, "result": json.loads(run.stdout)}
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
