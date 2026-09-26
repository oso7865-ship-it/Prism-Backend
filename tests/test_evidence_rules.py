import json

import pytest

from app.domain.analysis.analyzer import evaluate
from app.domain.review.policy import prepare, validate_result


def response(**changes):
    issue = dict(
        file_id="f1",
        line=2,
        evidence_lines=[1, 2],
        basis="SUPPORTED",
        severity="WARNING",
        trigger="user가 null인 분기",
        consequence="null 역참조",
        assumptions=[],
        title="null 분기",
        evidence="조건과 접근이 같은 분기에 있음",
        suggestion="null일 때 반환",
    )
    issue.update(changes)
    return json.dumps(dict(summary="검토", issues=[issue], limitations="실행 미검증"))


@pytest.mark.parametrize(
    "changes",
    [
        {"evidence_lines": [2, 99]},
        {"evidence_lines": [2, 2]},
        {"evidence_lines": [1]},
        {"line": 1, "evidence_lines": [1]},
        {"assumptions": ["보이지 않는 호출부"]},
        {"basis": "NEEDS_CONTEXT"},
        {"trigger": "  "},
        {"consequence": " "},
        {"evidence_lines": [True, 2]},
        {"basis": "NEEDS_CONTEXT", "assumptions": [" "]},
        {"basis": "NEEDS_CONTEXT", "assumptions": ["x" * 401]},
    ],
)
def test_evidence_rejects_invented_anchors_context_only_and_inconsistent_basis(changes):
    bundle = prepare(
        [
            {
                "filename": "a.js",
                "patch": "@@ -1 +1,2 @@\n function f(user) {\n+ if(user===null)return user.name;",
            }
        ],
        [],
        [],
    )
    with pytest.raises(ValueError):
        validate_result(response(**changes), bundle)


def test_evidence_keeps_uncertainty_visible_and_does_not_silently_filter():
    bundle = prepare(
        [{"filename": "a.js", "patch": "@@ -0,0 +1,2 @@\n+function f(user){\n+return user.name;}"}],
        [],
        [],
    )
    result = validate_result(
        response(basis="NEEDS_CONTEXT", assumptions=["null 입력 가능 여부"]), bundle
    )
    assert len(result["issues"]) == 1
    assert result["issues"][0]["assumptions"] == ["null 입력 가능 여부"]
    assert "file_id" not in result["issues"][0]


@pytest.mark.parametrize(
    "path,source,rule",
    [
        ("x.py", "from mod import *\neval(value)", "PY-004"),
        ("x.py", "globals()['eval']=custom\neval(value)", "PY-004"),
        ("x.py", "def f(exec):\n exec(value)", "PY-005"),
        ("x.py", "class Exception: pass\ntry:\n work()\nexcept Exception:\n raise", "PY-008"),
        ("x.js", "const eval=custom; eval(value);", "JS-005"),
        ("x.ts", "import {Function} from 'custom'; new Function(value);", "JS-006"),
        ("x.js", "globalThis.Function=custom; new Function(value);", "JS-006"),
        ("x.js", "eval(code); new Function(value);", "JS-006"),
    ],
)
def test_ambiguous_builtins_are_unevaluated(path, source, rule):
    result = evaluate(path, source.encode())
    assert result.status == "INCLUDED"
    assert rule in result.not_evaluated and rule not in result.evaluated
    assert rule not in {f.rule_id for f in result.findings}


@pytest.mark.parametrize(
    "path,source,line",
    [
        ("x.py", "if a:\n if b:\n  if c:\n   if d:\n    if e:\n     work()", 5),
        ("x.java", "class A {void f(){\nif(a){if(b){if(c){if(d){if(e){work();}}}}}}}", 2),
        ("x.js", "if(a){if(b){if(c){if(d){\nif(e){work();}}}}}", 2),
        ("x.ts", "if(a){if(b){if(c){if(d){\nif(e){work();}}}}}", 2),
    ],
)
def test_nested_control_location_all_languages(path, source, line):
    result = evaluate(path, source.replace("\n", "\r\n").encode())
    matches = [f for f in result.findings if f.rule_id == "COM-003"]
    assert len(matches) == 1 and matches[0].start_line == line


@pytest.mark.parametrize(
    "path,source",
    [
        ("x.js", "if(a){if(b){if(c){if(d){function f(){if(e){work();}}}}}}"),
        ("x.py", "if a:\n if b:\n  if c:\n   if d:\n    def f():\n     if e:\n      work()"),
        ("x.py", "if a:\n pass\nelif b:\n pass\nelif c:\n pass\nelif d:\n pass\nelif e:\n pass"),
        ("x.java", "class A{void f(){if(a){}else if(b){}else if(c){}else if(d){}else if(e){}}}"),
    ],
)
def test_function_boundaries_and_else_if_do_not_inflate_depth(path, source):
    result = evaluate(path, source.encode())
    assert result.status == "INCLUDED"
    assert "COM-003" not in {f.rule_id for f in result.findings}


@pytest.mark.parametrize(
    "source",
    [
        'try:\n work()\nexcept factory("Exception"):\n raise',
        "try:\n work()\nexcept CustomException:\n raise",
        "try:\n work()\nexcept errors.Exception:\n raise",
    ],
)
def test_broad_except_uses_syntax_not_header_substring(source):
    result = evaluate("a.py", source.encode())
    assert "PY-008" not in {f.rule_id for f in result.findings}


def test_new_rules_expose_static_messages_and_unresolved_reason():
    from app.domain.analysis.contracts import RULES

    result = evaluate("x.ts", b"const Function=custom; new Function(input);")
    assert result.reason == "BINDING_UNRESOLVED"
    assert "JS-006" in result.not_evaluated
    result = evaluate("x.py", b"# test\neval(user_input)")
    finding = next(f for f in result.findings if f.rule_id == "PY-004")
    assert finding.start_line == 2 and finding.end_line == 2
    assert RULES[finding.rule_id].severity == "WARNING"
    assert RULES[finding.rule_id].confidence == "MEDIUM"
    assert "미검증" in RULES[finding.rule_id].message
    assert "user_input" not in result.model_dump_json()
