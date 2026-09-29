"""Finite constant propagation over a tiny pure syntax subset, never a project runtime."""

import ast
import json
import re
from typing import Any

from app.domain.review.semantics import interpret


class Unsupported(ValueError):
    pass


class Projection:
    def __init__(self, functions: dict[str, ast.FunctionDef]):
        self.functions = functions
        self.steps = 0
        self.branches: list[dict[str, object]] = []
        self.visited: set[int] = set()

    def value(self, node: ast.expr, bindings: dict[str, Any], depth: int) -> Any:
        self.steps += 1
        if self.steps > 160 or depth > 4:
            raise Unsupported

        def read(n: ast.expr) -> Any:
            return self.value(n, bindings, depth)

        if isinstance(node, ast.Dict) and len(node.keys) <= 8:
            if any(not isinstance(k, ast.Constant) or type(k.value) is not str for k in node.keys):
                raise Unsupported
            return {
                read(k): read(v)
                for k, v in zip(node.keys, node.values, strict=True)
                if k is not None
            }
        if isinstance(node, ast.List) and len(node.elts) <= 16:
            return [read(n) for n in node.elts]
        if isinstance(node, ast.BoolOp):
            value = read(node.values[0])
            for part in node.values[1:]:
                if (isinstance(node.op, ast.Or) and value) or (
                    isinstance(node.op, ast.And) and not value
                ):
                    break
                value = read(part)
            return value
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = read(node.left), read(node.comparators[0])
            if isinstance(node.ops[0], (ast.Is, ast.IsNot)):
                if right is not None and type(right) is not bool:
                    raise Unsupported
                same = left is right
                return not same if isinstance(node.ops[0], ast.IsNot) else same
            if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                same = left == right
                return not same if isinstance(node.ops[0], ast.NotEq) else same
            raise Unsupported
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and not node.keywords
            ):
                target = read(node.func.value)
                args = [read(a) for a in node.args]
                if type(target) is dict and 1 <= len(args) <= 2 and type(args[0]) is str:
                    return target.get(*args)
                raise Unsupported
            if isinstance(node.func, ast.Name) and node.func.id in self.functions:
                if node.func.id in bindings or any(k.arg is None for k in node.keywords):
                    raise Unsupported
                return self.call(
                    node.func.id,
                    [read(a) for a in node.args],
                    {k.arg: read(k.value) for k in node.keywords if k.arg is not None},
                    depth + 1,
                )
        # Names/constants/arithmetic/list/range have separate finite resource bounds.
        return interpret(node, bindings)

    def call(self, name: str, args: list[Any], kwargs: dict[str, Any], depth: int) -> Any:
        if depth > 4 or name not in self.functions:
            raise Unsupported
        fn = self.functions[name]
        parameters = fn.args
        if (
            fn.decorator_list
            or parameters.vararg
            or parameters.kwarg
            or parameters.kwonlyargs
            or parameters.posonlyargs
        ):
            raise Unsupported
        names = [a.arg for a in parameters.args]
        if len(names) > 4 or len(args) > len(names) or not set(kwargs) <= set(names):
            raise Unsupported
        if set(names[: len(args)]) & set(kwargs):
            raise Unsupported
        if any(
            isinstance(n, ast.Name)
            and isinstance(n.ctx, ast.Store)
            and n.id in {"range", "list", "len", "min", "max"}
            for n in ast.walk(fn)
        ) or set(names) & {"range", "list", "len", "min", "max"}:
            raise Unsupported
        bindings = {
            n: self.value(v, {}, depth)
            for n, v in zip(
                names[len(names) - len(parameters.defaults) :], parameters.defaults, strict=True
            )
        }
        bindings.update(zip(names, args))
        bindings.update(kwargs)
        if set(bindings) != set(names):
            raise Unsupported

        def block(nodes: list[ast.stmt]) -> tuple[bool, Any]:
            for node in nodes:
                self.visited.add(node.lineno)
                self.steps += 1
                if self.steps > 160:
                    raise Unsupported
                if isinstance(node, ast.Return) and node.value is not None:
                    return True, self.value(node.value, bindings, depth)
                if (
                    isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                ):
                    bindings[node.targets[0].id] = self.value(node.value, bindings, depth)
                elif isinstance(node, ast.If):
                    condition = bool(self.value(node.test, bindings, depth))
                    self.branches.append(
                        {"function": name, "line": node.lineno, "condition": condition}
                    )
                    returned, value = block(node.body if condition else node.orelse)
                    if returned:
                        return True, value
                elif (
                    isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant)
                    and type(node.value.value) is str
                ):
                    continue
                else:
                    raise Unsupported
            return False, None

        returned, value = block(fn.body)
        if not returned:
            raise Unsupported
        return value


def python_observations(file: dict[str, Any]) -> list[dict[str, object]]:
    rows = file["lines"]
    if not rows or [r["line"] for r in rows] != list(range(1, len(rows) + 1)):
        return []
    source = "\n".join(r["code"] for r in rows)
    if len(source.encode()) > 16384:
        return []
    tree = ast.parse(source)
    if len(list(ast.walk(tree))) > 500 or any(
        not isinstance(n, ast.FunctionDef) for n in tree.body
    ):
        return []
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if len(functions) != len(tree.body):
        return []
    observations = []
    for assertion in (n for n in ast.walk(tree) if isinstance(n, ast.Assert)):
        test = assertion.test
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], (ast.Eq, ast.Is))
            and isinstance(test.left, ast.Call)
            and isinstance(test.left.func, ast.Name)
        ):
            continue
        call = test.left
        assert isinstance(call.func, ast.Name)
        projection = Projection(functions)
        try:
            # Literal arguments only: no executing a test body/fixture to obtain bindings.
            literal_nodes = [*call.args, *(k.value for k in call.keywords), *test.comparators]
            if any(
                isinstance(n, (ast.Call, ast.Name, ast.Attribute, ast.Subscript))
                for literal in literal_nodes
                for n in ast.walk(literal)
            ):
                continue
            args = [projection.value(a, {}, 0) for a in call.args]
            kwargs = {
                k.arg: projection.value(k.value, {}, 0) for k in call.keywords if k.arg is not None
            }
            if len(kwargs) != len(call.keywords):
                continue
            expected = projection.value(test.comparators[0], {}, 0)
            value = projection.call(call.func.id, args, kwargs, 1)
            if (
                isinstance(test.ops[0], ast.Is)
                and expected is not None
                and type(expected) is not bool
            ):
                continue
            matches = value is expected if isinstance(test.ops[0], ast.Is) else value == expected
            observations.append(
                {
                    "test_line": assertion.lineno,
                    "function": call.func.id,
                    "arguments": args,
                    "keywords": kwargs,
                    "value": value,
                    "asserted_value": expected,
                    "comparison": type(test.ops[0]).__name__,
                    "matches_assertion": matches,
                    "branches": projection.branches,
                    "visited_lines": sorted(projection.visited),
                }
            )
        except (Unsupported, ValueError, TypeError, KeyError, RecursionError):
            continue
        if len(observations) == 6:
            break
    return sorted(observations, key=lambda row: bool(row["matches_assertion"]))


def java_observations(file: dict[str, Any]) -> list[dict[str, object]]:
    # Complete single arithmetic method only. A guard/overload/helper is out of scope.
    rows = file["lines"]
    if not rows or [r["line"] for r in rows] != list(range(1, len(rows) + 1)):
        return []
    source = "\n".join(r["code"] for r in rows)
    match = re.fullmatch(
        r"\s*(?:public\s+)?class\s+\w+\s*\{\s*(?:public\s+)?(?:static\s+)?long\s+\w+\(int\s+(\w+),\s*int\s+(\w+)\)\s*\{\s*return\s+(\(long\)\s*)?(\w+)\s*\*\s*(\w+)\s*;\s*\}\s*\}\s*",
        source,
    )
    if not match or match[1] == match[2] or match.group(1, 2) != match.group(4, 5):
        return []
    width = 64 if match.group(3) else 32
    result = []
    for a, b in [(0, 1), (3, 4), (100000, 100000)]:
        product = a * b
        value = (product + (1 << (width - 1))) % (1 << width) - (1 << (width - 1))
        result.append(
            {
                "inputs": {match[1]: a, match[2]: b},
                "operation_bits": width,
                "returned_long": value,
                "mathematical_product": product,
                "preserves_product": value == product,
            }
        )
    return result


def path_facts(payload: str) -> list[dict[str, object]]:
    facts = []
    for file in json.loads(payload)["files"]:
        try:
            observations = (
                python_observations(file)
                if file["language"] == "py"
                else (java_observations(file) if file["language"] == "java" else [])
            )
        except (SyntaxError, ValueError, TypeError, RecursionError):
            continue
        if observations:
            facts.append(
                {
                    "file_id": file["file_id"],
                    "scope": "FINITE_STATIC_PROJECTION_NOT_RUNTIME",
                    "observations": observations,
                }
            )
        if len(facts) >= 4:
            break
    return facts
