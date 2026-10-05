"""Oracle checks for review-accuracy-v1. Reference functions are written here by hand.

Corpus source text is parsed (ast/regex) for consistency only; it is never executed, imported or
evaluated. The answers are therefore independent of the model and of the corpus strings.
"""

import ast
import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

from app.domain.review.semantics import interpret, parse
from scripts.build_accuracy_cases import PAIRS, build_cases

ROOT = Path("evals/review-accuracy-v1")


def classify(value):
    if value is None:
        return "NONE"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if value == "" and isinstance(value, str):
        return "EMPTY_STR"
    if value == [] and isinstance(value, list):
        return "EMPTY_LIST"
    if isinstance(value, int):
        return "ZERO" if value == 0 else f"INT:{value}"
    if isinstance(value, str):
        return f"STR:{value}"
    if isinstance(value, list):
        return f"LIST:{value}"
    raise AssertionError(type(value))


def outcome(function, inputs):
    try:
        return classify(function(**inputs))
    except Exception as exc:  # noqa: BLE001 - the oracle classifies any exception by type
        return f"EXC:{type(exc).__name__}"


def window_contract(total, step):
    result, position = [], 0
    while position < total:
        result.append(position)
        position += step
    return result


def last_indexes_contract(count, size):
    result, index = [], size - 1
    while len(result) < count:
        result.append(index)
        index -= 1
    return result


def last_item_contract(items):
    return None if len(items) == 0 else items[len(items) - 1]


def pages_contract(count, pageSize):  # noqa: N803 - mirrors the Java parameter name
    return (count + pageSize - 1) // pageSize


REF = {
    "or-default-name": dict(
        contract=lambda name, fallback: fallback if name is None else name,
        defect=lambda name, fallback: name or fallback,
        clean=lambda name, fallback: fallback if name is None else name,
    ),
    "or-default-pagesize": dict(
        contract=lambda requested, default_size: default_size if requested is None else requested,
        defect=lambda requested, default_size: requested or default_size,
        clean=lambda requested, default_size: default_size if requested is None else requested,
    ),
    "default-arg-notify": dict(
        contract=lambda enabled=True, urgent=False: enabled or urgent,
        defect=lambda enabled=True, urgent=False: enabled and urgent,
        clean=lambda enabled=True, urgent=False: urgent or enabled,
    ),
    "default-arg-retries": dict(
        contract=lambda max_retries=3, used=0: max_retries - used,
        defect=lambda max_retries=3, used=1: max_retries - used,
        clean=lambda max_retries=3, used=0: max_retries - used,
    ),
    "range-step-offsets": dict(
        contract=window_contract,
        defect=lambda total, step: list(range(0, total, step - 1)),
        clean=lambda total, step: list(range(0, total, step)),
    ),
    "range-step-last": dict(
        contract=last_indexes_contract,
        defect=lambda count, size: list(range(size - 1, size - count, 1)),
        clean=lambda count, size: list(range(size - 1, size - 1 - count, -1)),
    ),
    "dict-get-timeout": dict(
        contract=lambda config: config["timeout"] if "timeout" in config else 30,
        defect=lambda config: config.get("timeout") or 30,
        clean=lambda config: config.get("timeout", 30),
    ),
    "dict-get-flag": dict(
        contract=lambda flags, name: name in flags and flags[name] is True,
        defect=lambda flags, name: flags.get(name, True),
        clean=lambda flags, name: flags.get(name, False) is True,
    ),
    "none-vs-falsy-items": dict(
        contract=lambda items: items is not None,
        defect=lambda items: bool(items),
        clean=lambda items: items is not None,
    ),
    "none-vs-falsy-text": dict(
        contract=lambda text: None if text is None else text.strip(),
        defect=lambda text: None if not text else text.strip(),
        clean=lambda text: None if text is None else text.strip(),
    ),
    "length-fits": dict(
        contract=lambda name: len(name) <= 8,
        defect=lambda name: len(name) < 8,
        clean=lambda name: not len(name) > 8,
    ),
    "length-last": dict(
        contract=last_item_contract,
        defect=lambda items: None if len(items) == 0 else items[len(items)],
        clean=lambda items: None if len(items) == 0 else items[-1],
    ),
    "java-null-empty": dict(
        contract=lambda name, fallback: fallback if name is None else name,
        defect=lambda name, fallback: fallback if name is None or name == "" else name,
        clean=lambda name, fallback: fallback if name is None else name,
    ),
    "java-length-tag": dict(
        contract=lambda tag: len(tag) <= 16,
        defect=lambda tag: len(tag) < 16,
        clean=lambda tag: not len(tag) > 16,
    ),
    "java-pages": dict(
        contract=pages_contract,
        defect=lambda count, pageSize: count // pageSize,  # noqa: N803
        clean=lambda count, pageSize: (count + pageSize - 1) // pageSize,  # noqa: N803
    ),
    "java-access": dict(
        contract=lambda active, admin, owner: active and (admin or owner),
        defect=lambda active, admin, owner: (active and admin) or owner,
        clean=lambda active, admin, owner: active and (owner or admin),
    ),
}

CASES = build_cases()
BY_PAIR = {p["pair"]: p for p in PAIRS}


def test_reference_table_covers_every_pair():
    assert set(REF) == set(BY_PAIR)
    assert len(PAIRS) == 16
    assert len(CASES) == 32


@pytest.mark.parametrize("pair", sorted(BY_PAIR))
def test_probes_match_independent_reference_behaviour(pair):
    reference = REF[pair]
    for probe in BY_PAIR[pair]["probes"]:
        inputs = probe["inputs"]
        assert outcome(reference["defect"], inputs) == probe["actual"], (pair, inputs)
        assert outcome(reference["contract"], inputs) == probe["expected"], (pair, inputs)
        assert outcome(reference["clean"], inputs) == probe["expected"], (pair, inputs)


@pytest.mark.parametrize("pair", sorted(BY_PAIR))
def test_defect_diverges_from_contract_on_a_probe_and_clean_never_does(pair):
    probes = BY_PAIR[pair]["probes"]
    assert any(p["actual"] != p["expected"] for p in probes), pair
    for probe in probes:
        assert outcome(REF[pair]["clean"], probe["inputs"]) == probe["expected"]


@pytest.mark.parametrize("pair", sorted(BY_PAIR))
def test_reference_signature_matches_corpus_source_without_executing_it(pair):
    spec = BY_PAIR[pair]
    for polarity in ("defect", "clean"):
        source = spec[polarity][0]
        if spec["lang"] == "py":
            tree = ast.parse(source)
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
            names = [a.arg for a in function.args.args]
        else:
            signature = re.search(r"static\s+\w+\s+\w+\(([^)]*)\)", source)
            assert signature
            names = [p.split()[-1] for p in signature.group(1).split(",")]
        assert names == list(inspect.signature(REF[pair][polarity]).parameters), (pair, polarity)
        for probe in spec["probes"]:
            assert set(probe["inputs"]) <= set(names), (pair, probe["inputs"])


def test_interpreter_agrees_with_reference_on_expression_cases():
    cases = [
        ("name or fallback", dict(name="", fallback="guest"), "guest"),
        ("requested or default_size", dict(requested=0, default_size=25), 25),
        ("enabled and urgent", dict(enabled=True, urgent=False), False),
        ("list(range(0, total, step))", dict(total=5, step=2), [0, 2, 4]),
    ]
    for expression, bindings, expected in cases:
        assert interpret(parse(expression), bindings) == expected


def test_case_structure_and_pairs():
    for case in CASES:
        assert case["polarity"] in {"defect", "clean"}
        assert ("semantic" in case) == (case["polarity"] == "defect")
        assert bool(case["expected_locations"]) == (case["polarity"] == "defect")
        assert case["patch"].startswith("@@ ")
        assert "contract" in case and "oracle" in case
    for pair in BY_PAIR:
        twins = [c for c in CASES if c["pair_id"] == pair]
        assert sorted(c["polarity"] for c in twins) == ["clean", "defect"]
        assert twins[0]["split"] == twins[1]["split"]
    defect_lines = {
        c["id"]: c["expected_locations"][0][0] for c in CASES if c["polarity"] == "defect"
    }
    for case in CASES:
        if case["polarity"] == "defect":
            # The expected line must be a '+' line of the patch, not context.
            target = defect_lines[case["id"]]
            new_line = 0
            added = set()
            for row in case["patch"].splitlines()[1:]:
                if row.startswith("-"):
                    continue
                new_line += 1
                if row.startswith("+"):
                    added.add(new_line)
            assert target in added, case["id"]


def test_dev_holdout_split_is_stratified_and_disjoint():
    dev = [c for c in CASES if c["split"] == "dev"]
    holdout = [c for c in CASES if c["split"] == "holdout"]
    assert (len(dev), len(holdout)) == (20, 12)
    assert sum(c["polarity"] == "defect" for c in holdout) == 6
    assert sum(c["polarity"] == "defect" for c in dev) == 10
    assert {c["pair_id"] for c in dev}.isdisjoint({c["pair_id"] for c in holdout})
    assert {c["language"] for c in holdout} == {"py", "java"}
    assert len({c["category"] for c in CASES}) == 8


def test_frozen_manifest_matches_corpus_files():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["independent_human_review"] is False
    for split in ("dev", "holdout"):
        path = ROOT / f"cases-{split}.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["corpora"][split]["sha256"]
        stored = json.loads(path.read_text(encoding="utf-8"))
        assert [c["id"] for c in stored] == manifest["corpora"][split]["case_ids"]
        assert stored == [c for c in CASES if c["split"] == split]


def test_labels_are_not_part_of_the_model_payload():
    from app.domain.review.policy import prepare

    for case in CASES:
        bundle = prepare([{"filename": case["path"], "patch": case["patch"]}], [], [], 1)
        text = bundle.payload
        assert bundle.anchors, case["id"]
        for secret in ("oracle", "semantic", "expected_locations", "rubric", "polarity"):
            assert secret not in text, (case["id"], secret)
