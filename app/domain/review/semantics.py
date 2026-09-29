"""Small, bounded expression interpreter. Never executes analyzed Python or imports it."""

import ast
import itertools
import json
import operator
import re
from typing import Any

from app.domain.review.output_schema import ExpressionRepair, Issue

REVISION = "expressions-1"
UNKNOWN = "UNSUPPORTED"
OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul}


def parse(expression: str) -> ast.expr:
    if len(expression) > 160:
        raise ValueError(UNKNOWN)
    node = ast.parse(expression, mode="eval").body
    if len(list(ast.walk(node))) > 40:
        raise ValueError(UNKNOWN)
    return node


def interpret(node: ast.expr, bindings: dict[str, Any], depth: int = 0) -> Any:
    if depth > 12:
        raise ValueError(UNKNOWN)

    def read(child: ast.expr) -> Any:
        return interpret(child, bindings, depth + 1)

    if isinstance(node, ast.Constant) and type(node.value) in (int, bool, str, type(None)):
        value = node.value
        if (type(value) is int and abs(value) > 10**10) or (
            isinstance(value, str) and len(value) > 64
        ):
            raise ValueError(UNKNOWN)
        return value
    if isinstance(node, ast.Name) and node.id in bindings:
        return bindings[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = read(node.operand)
        if type(value) is not int:
            raise ValueError(UNKNOWN)
        return -value
    if isinstance(node, ast.BoolOp):
        value = read(node.values[0])
        for part in node.values[1:]:
            if (isinstance(node.op, ast.Or) and value) or (
                isinstance(node.op, ast.And) and not value
            ):
                break
            value = read(part)
        return value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left, right = read(node.left), read(node.right)
        if type(left) is not int or type(right) is not int:
            raise ValueError(UNKNOWN)
        value = OPERATORS[type(node.op)](left, right)
        if abs(value) > 10**10:
            raise ValueError(UNKNOWN)
        return value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
        name = node.func.id
        if name not in {"range", "list", "len", "min", "max"} or len(node.args) > 3:
            raise ValueError(UNKNOWN)
        args = [read(arg) for arg in node.args]
        if name == "range" and 1 <= len(args) <= 3 and all(type(v) is int for v in args):
            sequence = range(*args)
            if len(sequence) > 32:
                raise ValueError(UNKNOWN)
            return list(sequence)
        if name == "list" and len(args) == 1 and type(args[0]) is list:
            return args[0]
        if name == "len" and len(args) == 1 and type(args[0]) in (str, list):
            return len(args[0])
        if name in {"min", "max"} and 1 < len(args) <= 3 and all(type(v) is int for v in args):
            return min(args) if name == "min" else max(args)
    raise ValueError(UNKNOWN)


def observation(node: ast.expr, bindings: dict[str, Any]) -> dict[str, object]:
    try:
        return {"value": interpret(node, bindings)}
    except (ZeroDivisionError, TypeError) as exc:
        return {"exception": type(exc).__name__}
    except ValueError as exc:
        return {"unknown": True} if str(exc) == UNKNOWN else {"exception": "ValueError"}


def samples(node: ast.expr) -> list[dict[str, Any]]:
    names = sorted(
        {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        - {
            "range",
            "list",
            "len",
            "min",
            "max",
        }
    )
    if len(names) > 2:
        return []
    values: list[Any] = [-1, 0, 1, 3, None, "", False]
    return [
        dict(zip(names, values_at, strict=True))
        for values_at in itertools.product(values, repeat=len(names))
    ][:49]


def repair_check(repair: ExpressionRepair | None, file: dict[str, Any]) -> dict[str, object]:
    unknown: dict[str, object] = {"status": "NOT_VERIFIED", "samples": 0}
    if repair is None or file["language"] != "py":
        return unknown
    row = next((r for r in file["lines"] if r["line"] == repair.line), None)
    if not row or row["code"].strip() != "return " + repair.before.strip():
        return {"status": "SOURCE_MISMATCH", "samples": 0}
    try:
        before, after = parse(repair.before), parse(repair.after)
        probes = samples(before)
    except (SyntaxError, ValueError, RecursionError):
        return unknown
    checked = 0
    changed: list[dict[str, object]] = []
    for bindings in probes:
        old, new = observation(before, bindings), observation(after, bindings)
        if "unknown" in old or "unknown" in new or "exception" in old:
            continue
        checked += 1
        if json.dumps(old, sort_keys=True) != json.dumps(new, sort_keys=True):
            changed.append({"inputs": bindings, "before": old, "after": new})
    return {
        "status": "CHANGES_SUCCESSFUL_SAMPLES"
        if changed
        else ("PRESERVES_SAMPLES" if checked else "NOT_VERIFIED"),
        "samples": checked,
        "counterexamples": changed[:2],
        "scope": "EXPRESSION_ONLY_ASSUMING_BUILTINS",
    }


def suggestion_check(issue: Issue, file: dict[str, Any]) -> dict[str, object]:
    structured = None
    if issue.expression_repair is not None:
        structured = repair_check(issue.expression_repair, file)
        if structured["status"] not in {"SOURCE_MISMATCH", "NOT_VERIFIED"}:
            return structured
    if file["language"] == "py":
        rows = [
            r
            for r in file["lines"]
            if r["line"] in issue.evidence_lines
            and r["code"].strip().startswith("return list(range(")
        ]
        # A textual mention is NOT an applied patch. Only compare its stated expression
        # when exactly one provided return expression can anchor it unambiguously.
        if len(rows) == 1:
            before = rows[0]["code"].strip()[7:]
            choices = re.findall(r"\brange\([^()\n]{1,64}\)", issue.suggestion)[:3]
            for choice in choices:
                if len(before) > 160:
                    break
                check = repair_check(
                    ExpressionRepair(
                        line=rows[0]["line"],
                        before=before,
                        after=f"list({choice})",
                    ),
                    file,
                )
                if check["status"] == "CHANGES_SUCCESSFUL_SAMPLES":
                    check["inferred_from_text"] = True
                    return check
    return structured or {"status": "NOT_VERIFIED", "samples": 0}


def facts(payload: str) -> list[dict[str, object]]:
    """Illustrative exact operations, not a verdict on a complete function or its contract."""
    result: list[dict[str, object]] = []
    for file in json.loads(payload)["files"]:
        for row in file["lines"]:
            if not row["changed"]:
                continue
            code = row["code"].strip()
            if file["language"] == "py" and code.startswith("return "):
                try:
                    node = parse(code[7:])
                    observations = [
                        {"inputs": bindings, **observation(node, bindings)}
                        for bindings in samples(node)
                    ]
                    observations = [p for p in observations if "unknown" not in p][:7]
                    if observations:
                        result.append(
                            {
                                "file_id": file["file_id"],
                                "line": row["line"],
                                "scope": "EXPRESSION_ONLY_ASSUMING_BUILTINS",
                                "observations": observations,
                            }
                        )
                except (SyntaxError, ValueError, RecursionError):
                    continue
            elif file["language"] == "py" and re.search(r"\bor\b", code):
                result.append(
                    {
                        "file_id": file["file_id"],
                        "line": row["line"],
                        "scope": "OPERATOR_ONLY",
                        "observations": [
                            {"expression": "None or ''", "value": ""},
                            {"expression": "'' or None", "value": None},
                        ],
                    }
                )
            if len(result) >= 6:
                return result
    return result
