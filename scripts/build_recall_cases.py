"""Author-controlled evaluation data, never execute source embedded in the corpus."""

import hashlib
import json
from pathlib import Path


def case(identity, path, source, changed, expected, contract, provenance=None):
    lines = source.strip().splitlines()
    return {
        "id": identity,
        "path": path,
        "patch": f"@@ -1,{len(lines) - len(changed)} +1,{len(lines)} @@\n"
        + "\n".join(("+" if i in changed else " ") + line for i, line in enumerate(lines, 1)),
        "expected_locations": expected,
        "expected_lines": [],
        "contract": contract,
        "kind": "contract-preserving-public-pr-reproduction" if provenance else "authored-holdout",
        "label_review": "agent-oracle-and-source-inspected; independent-human-review-pending",
        "provenance": provenance,
        "rubric": {
            "required_behavior": contract,
            "reject": (
                "unreachable trigger, wrong effect, invented contract, duplicate "
                "or generic question"
            ),
        },
    }


def core_cases():
    length = """def content_length(body: str | bytes) -> int:
    return LENGTH

def prepare(body: str | bytes):
    wire = body.encode("utf-8") if isinstance(body, str) else body
    return {"Content-Length": content_length(body), "body": wire}

def test_protocol_length():
    for body in ["", "abc", "한글", b"abc", "한글".encode("utf-8")]:
        request = prepare(body)
        assert request["Content-Length"] == len(request["body"])
"""
    ca = """def merge_setting(request_value, session_value):
    if session_value is None:
        return request_value
    if request_value is None:
        return session_value
    return request_value

def environment_settings(env: dict[str, str], verify=True, session_verify=True):
    if verify is True or verify is None:
        verify = env.get("REQUESTS_CA_BUNDLE") or env.get("CURL_CA_BUNDLE")FALLBACK
    return merge_setting(verify, session_verify)

def test_environment_contract():
    assert environment_settings({}, True) is True
    assert environment_settings({"CURL_CA_BUNDLE": ""}, True) is True
    assert environment_settings({"REQUESTS_CA_BUNDLE": "", "CURL_CA_BUNDLE": ""}, True) is True
    assert environment_settings({"REQUESTS_CA_BUNDLE": "/ca.pem"}, True) == "/ca.pem"
    assert environment_settings({"CURL_CA_BUNDLE": "/ca.pem"}, False) is False
"""
    p_length = {
        "url": "https://github.com/psf/requests/pull/6589",
        "base_sha": "7a13c041dbef42f9f3feb14110f02626f6892e9a",
        "head_sha": "3fd309a5c14e4cfbd96bea6c8e71b4958fe090bb",
        "preserved": "Content-Length consumer, UTF-8 wire, str/bytes tests",
        "transformation": "handwritten minimal behavior reproduction; not original whole PR",
    }
    p_ca = {
        "url": "https://github.com/psf/requests/pull/6074",
        "base_sha": "5e749546a26ce62e53d0a14ae1455f8b066fe19f",
        "head_sha": "79c4a017fe341fb989d3a7876cf4e44b87601b58",
        "preserved": (
            "True/None guard, non-mapping setting merge, empty versus missing env, explicit False"
        ),
        "transformation": (
            "handwritten non-mapping branch; proxy/dict merging outside this contract"
        ),
    }
    cases = []
    for variant, operation, expected in [
        ("before", "len(body)", [[2, 2]]),
        ("after", 'len(body.encode("utf-8") if isinstance(body, str) else body)', []),
    ]:
        cases.append(
            case(
                f"length-{variant}",
                "length.py",
                length.replace("LENGTH", operation),
                [2],
                expected,
                (
                    "Content-Length must equal transmitted UTF-8 byte count, "
                    "including non-ASCII strings; bytes must not be encoded again."
                ),
                p_length,
            )
        )
    for variant, fallback, expected in [("before", "", [[10, 10]]), ("after", " or verify", [])]:
        cases.append(
            case(
                f"ca-{variant}",
                "settings.py",
                ca.replace("FALLBACK", fallback),
                [10],
                expected,
                (
                    "An empty CURL_CA_BUNDLE must preserve explicit verification "
                    "True. Missing values may become None but session merge restores "
                    "True. Explicit False and nonempty paths remain valid."
                ),
                p_ca,
            )
        )
    cases.append(
        case(
            "length-bytes-normal",
            "length.py",
            """def content_length(body: bytes) -> int:
    return len(body)

def prepare(body: bytes):
    return {"Content-Length": content_length(body), "body": body}

def test_bytes_contract():
    body = "한글".encode("utf-8")
    request = prepare(body)
    assert request["Content-Length"] == len(body)
""",
            [2],
            [],
            "Only bytes accepted and sent unchanged; len(bytes) already counts bytes.",
            p_length,
        )
    )
    cases.append(
        case(
            "ca-explicit-false-normal",
            "settings.py",
            ca.replace("FALLBACK", " or verify") + "\ndef test_explicit_disable():\n"
            '    assert environment_settings({"CURL_CA_BUNDLE": "/ca.pem"}, False) is False\n',
            [9, 10],
            [],
            (
                "The resolver must preserve an explicit False choice and accept "
                "CA path strings; do not invent a bool-only return contract."
            ),
            p_ca,
        )
    )
    return cases


def holdout_cases():
    pairs = [
        (
            "python-zip",
            "totals.py",
            """def total(prices: list[int], counts: list[int]) -> int:
    GUARD
    return sum(p * n for p, n in zip(prices, counts))

def test_contract():
    assert total([3, 4], [2, 1]) == 10
    try:
        total([3, 4], [2])
    except ValueError:
        return
    raise AssertionError("Mismatched lengths must be rejected, not silently truncated")
""",
            "pass",
            'if len(prices) != len(counts): raise ValueError("length mismatch")',
            2,
            "Reject unequal lengths; zip otherwise silently ignores unmatched entries.",
        ),
        (
            "java-ratio",
            "Ratio.java",
            """class Ratio {
    static double ratio(int used, int total) {
        if (total <= 0) throw new IllegalArgumentException();
        return DIVISION;
    }
    static void testContract() {
        if (ratio(1, 2) != 0.5) throw new AssertionError("fraction must be preserved");
        if (ratio(0, 2) != 0.0) throw new AssertionError("zero numerator is valid");
    }
}
""",
            "used / total",
            "(double) used / total",
            4,
            "Positive total is guarded; ratio(1,2) must be0.5, not integer-truncated0.",
        ),
        (
            "javascript-sum",
            "total.js",
            """function total(values) {
  return REDUCE;
}
function testContract() {
  if (total([]) !== 0) throw new Error("empty list must sum to zero");
  if (total([2, 3]) !== 5) throw new Error("sum mismatch");
}
""",
            "values.reduce((a, b) => a + b)",
            "values.reduce((a, b) => a + b, 0)",
            2,
            "Empty arrays are valid and must return0; reduce without initial value throws.",
        ),
        (
            "typescript-retries",
            "options.ts",
            """function retryCount(options: { retries?: number }): number {
  return DEFAULT;
}
function testContract() {
  if (retryCount({ retries: 0 }) !== 0) throw new Error("zero explicitly disables retries");
  if (retryCount({}) !== 3) throw new Error("only missing values use default3");
}
""",
            "options.retries || 3",
            "options.retries ?? 3",
            2,
            (
                "Zero must be preserved; only undefined options use3. Do not "
                "invent requirements for negatives."
            ),
        ),
    ]
    cases = []
    for identity, path, template, bad, good, line, contract in pairs:
        marker = next(m for m in ["GUARD", "DIVISION", "REDUCE", "DEFAULT"] if m in template)
        for suffix, operation, expected in [("bug", bad, [[line, line]]), ("fixed", good, [])]:
            cases.append(
                case(
                    identity + "-" + suffix,
                    path,
                    template.replace(marker, operation),
                    [line],
                    expected,
                    contract,
                )
            )
    return cases


if __name__ == "__main__":
    root = Path("evals/recall-repair")
    manifest = {
        "scope": "Labels and rubric never sent to model; test code is legitimate contract evidence",
        "independent_human_review": False,
        "corpora": {},
    }
    for name, data in [("core-v2", core_cases()), ("holdout-v1", holdout_cases())]:
        path = root / (name + ".json")
        with path.open("x", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        manifest["corpora"][name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "cases": len(data),
            "defects": sum(bool(c["expected_locations"]) for c in data),
        }
    with (root / "corpus-manifest.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")
