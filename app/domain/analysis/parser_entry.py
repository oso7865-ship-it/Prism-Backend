"""Trusted entry point for an untrusted-source parser subprocess."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.domain.analysis.analyzer import evaluate  # noqa: E402

if __name__ == "__main__":
    # Raw source is at most 200KiB; JSON escaping can expand it sixfold.
    raw = sys.stdin.buffer.read(1300000)
    request = json.loads(raw)
    result = evaluate(request["path"], request["source"].encode("utf-8"), request["ignored"])
    sys.stdout.write(result.model_dump_json())
