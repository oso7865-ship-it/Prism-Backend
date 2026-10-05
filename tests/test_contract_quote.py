import pytest

from app.domain.review.policy import quote_supported

PY = [
    "def label_for(name, fallback):",
    '    """Return the stored name. An empty string is intentional and must be returned',
    '    unchanged; only a missing name (None) uses the fallback."""',
    "    return name or fallback",
]
JAVA = [
    "class Names {",
    "    /** Display name. An empty string is intentional and returned unchanged;",
    "     * only null uses the fallback. */",
    "    static String display(String name, String fallback) {",
]
HASH = ["# Retries must never exceed three.", "# A zero value disables retries.", "x = 1"]


def supported(quote, lines):
    return quote_supported(quote, ["\n".join(lines), *lines], [lines])


def test_single_line_quote_is_unchanged():
    assert quote_supported("def label_for(name, fallback):", PY, [PY])


@pytest.mark.parametrize(
    ("quote", "lines"),
    [
        (
            "An empty string is intentional and must be returned unchanged; "
            "only a missing name (None) uses the fallback.",
            PY,
        ),
        (
            "An empty string is intentional and returned unchanged; only null uses the fallback.",
            JAVA,
        ),
        ("Retries must never exceed three. A zero value disables retries.", HASH),
        ("returned   unchanged;\n only a missing name", PY),
    ],
)
def test_sentence_wrapped_over_comment_lines_is_supported(quote, lines):
    # The wrapped sentence is not a plain substring of any single line.
    assert quote_supported(quote, lines, [lines])


@pytest.mark.parametrize(
    ("quote", "lines"),
    [
        ("An empty string is intentional and must always be returned", PY),
        ("only null uses the default", JAVA),
        ("A zero value enables retries.", HASH),
        ("Invented requirement", PY),
        ("", PY),
        ("   ", PY),
        # Words from two different files must not be stitched together.
        ("it must be returned Retries must never exceed three.", PY),
    ],
)
def test_invented_reworded_or_empty_quotes_are_rejected(quote, lines):
    other = [HASH] if lines is PY else [PY]
    assert not quote_supported(quote, ["\n".join(lines)], [lines, *other])


def test_order_of_words_must_be_preserved():
    assert not supported("fallback the uses name missing a only", PY)


def _bundle_and_draft(quote):
    import json
    from pathlib import Path

    from app.domain.review.policy import prepare

    cases = json.loads(Path("evals/review-accuracy-v1/cases-dev.json").read_text(encoding="utf-8"))
    case = next(c for c in cases if c["id"] == "or-default-name-defect")
    bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
    line = case["expected_locations"][0][0]
    issue = {
        "file_id": "f1",
        "line": line,
        "severity": "ERROR",
        "basis": "SUPPORTED",
        "evidence_lines": [line],
        "trigger": "name이 빈 문자열일 때",
        "consequence": "빈 문자열이 fallback으로 대체됩니다.",
        "assumptions": [],
        "title": "빈 문자열이 기본값으로 대체됨",
        "evidence": "name or fallback은 빈 문자열을 falsy로 취급합니다.",
        "suggestion": "name이 None일 때만 fallback을 쓰세요.",
        "contract_quote": quote,
    }
    return bundle, json.dumps({"summary": "s", "issues": [issue], "limitations": "l"})


def test_validate_result_accepts_a_wrapped_docstring_quote_end_to_end():
    from app.domain.review.policy import validate_result

    bundle, raw = _bundle_and_draft(
        "An empty string is intentional and must be returned unchanged; "
        "only a missing name (None) uses the fallback."
    )
    result = validate_result(raw, bundle)
    assert len(result["issues"]) == 1
    assert "contract_quote" not in result["issues"][0]  # still never stored


def test_validate_result_still_rejects_an_invented_quote():
    from app.domain.review.policy import validate_result

    bundle, raw = _bundle_and_draft("An empty string must always be replaced by the fallback.")
    with pytest.raises(ValueError, match="INVALID_CONTRACT_QUOTE"):
        validate_result(raw, bundle)
