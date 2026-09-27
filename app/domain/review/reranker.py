"""Optional loopback-only reranker. Failures are metadata, never a failed code review."""

import asyncio
import json
import math
import time
from typing import Protocol

import httpx

from app.domain.review.policy import SECRET
from app.domain.review.retrieval import Candidate, ranking_query

MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"


class Ranker(Protocol):
    async def rank(
        self, query: str, candidates: list[Candidate]
    ) -> tuple[list[int], dict[str, object]]: ...


class LocalReranker:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.transport = transport

    async def rank(
        self, query: str, candidates: list[Candidate]
    ) -> tuple[list[int], dict[str, object]]:
        fallback = list(range(len(candidates)))
        started = time.monotonic()
        metadata: dict[str, object] = {"mode": "rules", "candidate_count": len(candidates)}
        body = json.dumps(
            {
                "query": ranking_query(query),
                "documents": [c.code for c in candidates],
            },
            ensure_ascii=False,
        )
        if not candidates:
            return fallback, metadata
        if len(body.encode()) > 196608 or SECRET.search(body):
            return fallback, {**metadata, "fallback": "UNSAFE_RERANK_INPUT"}
        try:
            async with asyncio.timeout(2):
                async with httpx.AsyncClient(
                    transport=self.transport,
                    timeout=2,
                    trust_env=False,
                    follow_redirects=False,
                ) as client:
                    async with client.stream(
                        "POST",
                        "http://127.0.0.1:8091/rerank",
                        content=body.encode(),
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        response.raise_for_status()
                        raw = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=8193):
                            if len(raw) + len(chunk) > 8192:
                                raise ValueError("INVALID_RANKING")
                            raw.extend(chunk)
            data = json.loads(raw)
            values = data.get("scores")
            if (
                data.get("model") != MODEL
                or data.get("revision") != REVISION
                or not isinstance(values, list)
                or len(values) != len(candidates)
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                or type(data.get("truncated_documents")) is not int
                or not 0 <= data["truncated_documents"] <= len(candidates)
            ):
                raise ValueError("INVALID_RANKING")
            order = sorted(fallback, key=lambda i: (-values[i], i))
            metadata.update(
                mode="local_reranker",
                model=MODEL,
                revision=REVISION,
                truncated_documents=data["truncated_documents"],
            )
            return order, metadata
        except (TimeoutError, httpx.TimeoutException):
            metadata["fallback"] = "RERANK_TIMEOUT"
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            metadata["fallback"] = "RERANK_UNAVAILABLE_OR_INVALID"
        finally:
            metadata["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        return fallback, metadata
