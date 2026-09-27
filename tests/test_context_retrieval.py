import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.domain.review.context_selection import enrich
from app.domain.review.policy import MAX_INPUT, prepare, validate_result
from app.domain.review.reranker import MODEL, REVISION, LocalReranker
from app.domain.review.retrieval import Candidate, around, candidate_paths, inspect_sources, select
from scripts.evaluate_context_retrieval import SyntheticGitHub, build

CASES = json.loads(Path("evals/context-retrieval/cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_related_method_beyond_first_eighty_lines_and_diff_preservation(case):
    async def run():
        bundle, metrics = await build(case)
        assert metrics["candidate_hit"] and metrics["selected_hit"]
        assert metrics["candidate_count"] <= 24 and metrics["github_reads"] <= 22
        assert metrics["input_bytes"] <= MAX_INPUT
        before = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [])
        original = json.loads(before.payload)["files"][0]["lines"]
        after = json.loads(bundle.payload)["files"]
        assert [row for row in after[0]["lines"] if row["changed"]] == original
        assert sum(f.get("role") == "related" for f in after) <= 4
        assert any(max(row["line"] for row in f["lines"]) > 80 for f in after[1:])
        assert all(not row["changed"] for f in after[1:] for row in f["lines"])

    asyncio.run(run())


def test_syntax_metadata_preserves_decorators_and_does_not_execute_code():
    async def run():
        sources = {
            "a.py": [
                "@transaction",
                "def work(value):",
                "    return value",
                "raise RuntimeError('never run')",
            ]
        }
        result = await inspect_sources(sources)
        assert result["a.py"]["spans"] == [[1, 3, "work"]]
        assert around(sources["a.py"], 3, result["a.py"]) == [1, 2, 3]

    asyncio.run(run())


def test_candidate_limit_direct_imports_and_stable_ties():
    regular = {f"src/account{i}.py" for i in range(40)} | {"src/target.py"}
    info = {"src/account.py": {"imports": ["from target import load"], "identifiers": ["load"]}}
    ranked = candidate_paths(regular, {"src/account.py": []}, info)
    assert len(ranked) == 12 and ranked[0][0] == "src/target.py"
    assert ranked == candidate_paths(set(reversed(sorted(regular))), {"src/account.py": []}, info)


@pytest.mark.parametrize("module", ["./labels.js", "./labels", "../feature/labels.js"])
def test_explicit_esm_suffix_keeps_direct_import_candidate(module):
    changed = {"src/feature/display.js": []}
    regular = {"src/feature/labels.js", "src/unrelated.js"}
    metadata = {
        "src/feature/display.js": {
            "imports": [f'import {{ labelFor }} from "{module}";'],
            "identifiers": ["labelFor"],
        }
    }
    assert candidate_paths(regular, changed, metadata) == [("src/feature/labels.js", 100)]


def test_esm_helper_reaches_model_input_without_losing_changed_lines():
    cases = json.loads(Path("evals/quality-stabilization/holdout.json").read_text(encoding="utf-8"))
    case = next(c for c in cases if c["id"] == "js-import-safe")
    bundle, metrics = asyncio.run(build(case))
    assert metrics["candidate_hit"] and metrics["selected_hit"]
    files = json.loads(bundle.payload)["files"]
    assert len(files) == 2
    assert all(row["changed"] for row in files[0]["lines"])
    assert files[1]["role"] == "related"
    assert all(not row["changed"] for row in files[1]["lines"])


def test_secret_and_ignored_related_sources_never_reach_ranker():
    class Capture:
        async def rank(self, query, pool):
            assert all("secret_value" not in c.code for c in pool)
            assert all(not c.path.startswith("private/") for c in pool)
            return list(range(len(pool))), {"mode": "rules"}

    async def run():
        files = {
            "A.py": "from Store import load\nx = load()",
            "Store.py": "password='secret_value'",
            "private/Store.py": "def load(): return 1",
        }
        bundle = prepare(
            [
                {
                    "filename": "A.py",
                    "patch": "@@ -0,0 +1,2 @@\n+from Store import load\n+x = load()",
                }
            ],
            [],
            [],
        )
        github = SyntheticGitHub(files)
        result = await enrich(
            bundle, github, "none", "/repos/a/b", "b" * 40, ["private/*"], Capture()
        )
        assert "secret_value" not in result.payload
        assert all("private/Store.py" not in call for call in github.calls)
        assert any(
            n["reason"] == "RELATED_SOURCE_UNAVAILABLE" for n in result.coverage["context_notes"]
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    "failure", ["timeout", "unavailable", "extra", "nan", "wrong_revision", "bool", "html"]
)
def test_reranker_failure_returns_exact_rules_order_without_retry_or_source_echo(failure):
    calls = []

    async def transport(request):
        calls.append(request)
        assert str(request.url) == "http://127.0.0.1:8091/rerank"
        if failure == "timeout":
            raise httpx.ReadTimeout("private-code-must-not-leak")
        if failure == "unavailable":
            return httpx.Response(503)
        if failure == "html":
            return httpx.Response(200, text="private-code-must-not-leak")
        scores = {"extra": [1, 2, 3], "nan": [float("nan"), 1], "bool": [True, False]}.get(
            failure, [1, 2]
        )
        data = {
            "scores": scores,
            "model": MODEL,
            "revision": "other" if failure == "wrong_revision" else REVISION,
            "truncated_documents": 0,
        }
        return httpx.Response(200, content=json.dumps(data))

    async def run():
        pool = [Candidate("a.py", (1,), "a=1", 2), Candidate("b.py", (1,), "b=2", 1)]
        order, metadata = await LocalReranker(httpx.MockTransport(transport)).rank("code", pool)
        assert order == [0, 1] and metadata["mode"] == "rules"
        assert metadata["fallback"] and "private-code" not in json.dumps(metadata)
        assert len(calls) == 1

    asyncio.run(run())


def test_reranker_reorders_same_candidates_and_related_evidence_remains_nonprimary():
    def transport(request):
        return httpx.Response(
            200,
            json={
                "scores": [1, 3, 2],
                "model": MODEL,
                "revision": REVISION,
                "truncated_documents": 1,
            },
        )

    async def run():
        pool = [
            Candidate("a.py", (1,), "x=1", 4),
            Candidate("a.py", (2,), "x=2", 3),
            Candidate("b.py", (1,), "x=3", 2),
        ]
        order, metadata = await LocalReranker(httpx.MockTransport(transport)).rank("code", pool)
        assert order == [1, 2, 0] and metadata["mode"] == "local_reranker"
        assert [c.path for c in select(pool, order)] == ["a.py", "b.py"]
        bundle, _ = await build(CASES[0])
        related = json.loads(bundle.payload)["files"][1]
        line = related["lines"][0]["line"]
        issue = {
            "file_id": related["file_id"],
            "line": line,
            "evidence_lines": [line],
            "severity": "WARNING",
            "basis": "SUPPORTED",
            "assumptions": [],
            "title": "x",
            "trigger": "x",
            "consequence": "x",
            "evidence": "x",
            "suggestion": "x",
        }
        with pytest.raises(ValueError, match="INVALID_EVIDENCE_LINES"):
            validate_result(
                json.dumps({"summary": "x", "limitations": "x", "issues": [issue]}), bundle
            )

    asyncio.run(run())


def test_context_timeout_keeps_original_diff(monkeypatch):
    async def timeout(*args):
        raise TimeoutError()

    monkeypatch.setattr("app.domain.review.context_selection.collect", timeout)

    async def run():
        bundle = prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x=1"}], [], [])
        before = bundle.payload
        result = await enrich(bundle, None, "", "", "b" * 40, [])
        assert result.payload == before
        assert result.coverage["retrieval"]["mode"] == "diff_only"

    asyncio.run(run())


def test_reranker_oversized_stream_stops_reading_and_falls_back():
    class Oversized(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"x" * 8193
            pytest.fail("the rest of an oversized response must not be consumed")

    async def run():
        transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=Oversized()))
        pool = [Candidate("a.py", (1,), "x=1", 1)]
        order, meta = await LocalReranker(transport).rank("x", pool)
        assert order == [0] and meta["fallback"] == "RERANK_UNAVAILABLE_OR_INVALID"

    asyncio.run(run())


def test_syntax_cap_marks_incomplete_metadata():
    async def run():
        source = [f"def method_{i}(): return {i}" for i in range(129)]
        info = await inspect_sources({"a.py": source})
        assert len(info["a.py"]["spans"]) == 128 and info["a.py"]["partial"]

    asyncio.run(run())
