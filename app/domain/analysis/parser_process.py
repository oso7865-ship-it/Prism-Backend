"""Bounded process protocol; never writes customer source to disk."""

import asyncio
import json
import os
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

from app.domain.analysis.contracts import MAX_FILE, RULES, Evaluation


async def parse_file(
    path: str, source: bytes, ignored: bool = False, timeout: float = 5
) -> Evaluation:
    from app.domain.analysis.contracts import language_for

    if len(source) > MAX_FILE:
        return Evaluation(
            language=language_for(path), status="LIMIT_EXCEEDED", reason="FILE_SIZE_LIMIT"
        )
    try:
        content = source.decode("utf-8")
    except UnicodeDecodeError:
        return Evaluation(
            language=language_for(path), status="EXCLUDED", reason="ENCODING_UNSUPPORTED"
        )
    # Isolated Python ignores PYTHONPATH/user site; allow only Windows runtime necessities.
    env = {k: v for k, v in os.environ.items() if k.upper() in ("SYSTEMROOT", "WINDIR")}
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        [sys.executable, "-I", str(Path(__file__).with_name("parser_entry.py"))],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        creationflags=creationflags,
    )
    communication = asyncio.create_task(
        asyncio.to_thread(
            proc.communicate,
            json.dumps({"path": path, "source": content, "ignored": ignored}).encode(),
            timeout=timeout,
        )
    )
    try:
        data, _ = await asyncio.shield(communication)
        if proc.returncode != 0 or len(data) > 65536:
            return Evaluation(
                language=language_for(path), status="PARSE_ERROR", reason="PARSER_FAILED"
            )
        result = Evaluation.model_validate_json(data)
        if any(f.rule_id not in RULES or f.end_line < f.start_line for f in result.findings):
            raise ValueError("Invalid parser output")
        return result
    except subprocess.TimeoutExpired:
        return Evaluation(
            language=language_for(path), status="LIMIT_EXCEEDED", reason="PARSER_TIMEOUT"
        )
    finally:
        if proc.poll() is None:
            proc.kill()
        with suppress(subprocess.TimeoutExpired):
            await asyncio.shield(communication)
        await asyncio.to_thread(proc.wait)
        for stream in (proc.stdin, proc.stdout):
            if stream:
                stream.close()
