import asyncio
import json

from app.domain.review.context_selection import enrich
from app.domain.review.policy import prepare
from scripts.evaluate_context_retrieval import SyntheticGitHub


async def build(files, patch, ranker=None, per_file=16384):
    bundle = prepare([{"filename": "main.py", "patch": patch}], [], [], per_file=per_file)
    return await enrich(
        bundle,
        SyntheticGitHub(files),
        "none",
        "/repos/a/b",
        "b" * 40,
        [],
        ranker,
        per_file=per_file,
    )


def provided(bundle, path):
    data = json.loads(bundle.payload)
    return {
        r["line"]: r["code"]
        for f in data["files"]
        if bundle.anchors[f["file_id"]][0] == path
        for r in f["lines"]
    }


def test_adversarial_rank_cannot_remove_two_callees_from_same_file():
    class Reverse:
        async def rank(self, query, pool):
            return list(reversed(range(len(pool)))), {"mode": "test_reverse"}

    main = (
        "from helpers import require_user, count\ndef label(x):\n    return require_user(x)"
        "\ndef size(x):\n    return count(x)"
    )
    helper = "def require_user(x):\n    if x is None: raise ValueError()\n    return x\n"
    helper += "\n" * 110 + "def count(x):\n    return len(x)"
    patch = "@@ -0,0 +1,5 @@\n" + "\n".join("+" + r for r in main.splitlines())
    bundle = asyncio.run(build({"main.py": main, "helpers.py": helper}, patch, Reverse()))
    rows = provided(bundle, "helpers.py")
    assert rows[2].strip().startswith("if x is None")
    assert "    return len(x)" in rows.values()
    assert len(rows) == len(set(rows))
    assert bundle.coverage["retrieval"]["query_count"] >= 2
    assert bundle.coverage["retrieval"]["protected_missing"] == 0


def test_sixteen_kib_keeps_long_function_that_eight_kib_cannot_fit():
    lines = ["def compute(x):", "    if x is None: return 0"]
    lines += ["    # " + "padding " * 11 for _ in range(88)]
    lines += ["    return len(x)"]
    files = {"main.py": "\n".join(lines)}
    patch = f"@@ -91 +91 @@\n+{lines[-1]}"
    small = asyncio.run(build(files, patch, per_file=8192))
    large = asyncio.run(build(files, patch))
    assert 2 not in provided(small, "main.py")
    assert 2 in provided(large, "main.py")
    assert len(large.payload.encode()) <= 49152
    assert any(n["reason"] == "FUNCTION_PARTIAL" for n in small.coverage["context_notes"])


def test_multiple_changed_lines_in_one_function_do_not_consume_all_queries():
    from app.domain.review.context_plan import queries
    from app.domain.review.retrieval import inspect_sources

    sources = {
        "main.py": [
            "def first(x):",
            "    y = x + 1",
            "    return y",
            "def second(x):",
            "    return helper(x)",
        ]
    }
    meta = asyncio.run(inspect_sources(sources))
    groups, omitted = queries(
        [{"file_id": "f1", "lines": [{"line": n, "changed": True} for n in range(1, 6)]}],
        {"f1": "main.py"},
        sources,
        meta,
    )
    assert len(groups) == 2 and omitted == 0
    assert "helper" not in groups[0].calls and "helper" in groups[1].calls


def test_utf8_json_budget_rejects_oversized_diff_before_enrichment():
    patch = "@@ -0,0 +1,110 @@\n" + "\n".join("+" + "한" * 45 for _ in range(110))
    # Raw patch fits16KiB but the numbered JSON rows exceed it.
    assert len(patch.encode()) < 16384
    bundle = prepare(
        [
            {"filename": "main.py", "patch": patch},
            {"filename": "small.py", "patch": "@@ -0,0 +1 @@\n+x=1"},
        ],
        [],
        [],
    )
    assert bundle.coverage["excluded"][0]["reason"] == "PATCH_TOO_LARGE"


def test_direct_callee_outside_hunk_in_another_changed_file_is_preserved():
    main = "from helpers import require_user\ndef label(x):\n    return require_user(x).name"
    helper = "def require_user(x):\n    if x is None: raise ValueError()\n    return x\n"
    helper += "\n" * 110 + "def count(x):\n    return len(x)"
    changes = [
        {"filename": "main.py", "patch": "@@ -3 +3 @@\n+    return require_user(x).name"},
        {"filename": "helpers.py", "patch": "@@ -115 +115 @@\n+    return len(x)"},
    ]
    bundle = asyncio.run(
        enrich(
            prepare(changes, [], []),
            SyntheticGitHub({"main.py": main, "helpers.py": helper}),
            "none",
            "/repos/a/b",
            "b" * 40,
            [],
        )
    )
    rows = provided(bundle, "helpers.py")
    assert rows[2].strip() == "if x is None: raise ValueError()"
    assert rows[115] == "    return len(x)"
    assert len(bundle.payload.encode()) <= 49152
    assert all(f["role"] == "changed" for f in bundle.coverage["files"])
    assert bundle.coverage["retrieval"]["protected_missing"] == 0
