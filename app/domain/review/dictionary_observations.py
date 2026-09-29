"""Exact, bounded dictionary-get/or examples, not whole-program execution."""

import ast
import itertools
import json
import re


def dictionary_facts(payload: str) -> list[dict[str, object]]:
    facts: list[dict[str, object]] = []
    for file in json.loads(payload)["files"]:
        if file["language"] != "py":
            continue
        for row in file["lines"]:
            text = row["code"].strip()
            if not row["changed"] or len(text) > 240:
                continue
            expression = re.sub(r"^(?:[A-Za-z_]\w*\s*=\s*|return\s+)", "", text)
            try:
                node = ast.parse(expression, mode="eval").body
            except (SyntaxError, RecursionError):
                continue
            if (
                not isinstance(node, ast.BoolOp)
                or not isinstance(node.op, ast.Or)
                or len(node.values) != 2
            ):
                continue
            names, keys = [], []
            for child in node.values:
                if not (
                    isinstance(child, ast.Call)
                    and not child.keywords
                    and len(child.args) == 1
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "get"
                    and isinstance(child.func.value, ast.Name)
                    and isinstance(child.args[0], ast.Constant)
                    and isinstance(child.args[0].value, str)
                    and len(child.args[0].value) <= 64
                ):
                    break
                names.append(child.func.value.id)
                keys.append(child.args[0].value)
            if len(names) != 2 or names[0] != names[1]:
                continue
            examples = []
            for left, right in itertools.product([None, "", "example-value"], repeat=2):
                mapping = {k: v for k, v in zip(keys, (left, right), strict=True) if v is not None}
                # Only builtin dict values authored here; no analyzed object or call is used.
                value = mapping.get(keys[0]) or mapping.get(keys[1])
                examples.append({"inputs": {names[0]: mapping}, "value": value})
            facts.append(
                {
                    "file_id": file["file_id"],
                    "line": row["line"],
                    "scope": "EXPRESSION_ONLY_ASSUMING_BUILTIN_DICT",
                    "expression": expression,
                    "observations": examples,
                }
            )
            if len(facts) == 4:
                return facts
    return facts
