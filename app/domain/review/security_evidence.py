"""Narrow Python/Flask straight-line input-to-shell evidence, without code execution."""

import ast
import json


def scan(payload: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for file in json.loads(payload)["files"]:
        if file["language"] != "py" or file.get("role", "changed") != "changed":
            continue
        rows = {r["line"]: r for r in file["lines"]}
        if not rows or max(rows) > 2000:
            continue
        text = "\n".join(rows.get(n, {}).get("code", "") for n in range(1, max(rows) + 1))
        try:
            tree = ast.parse(text)
        except (SyntaxError, RecursionError):
            continue
        imports: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"os", "subprocess"}:
                        imports[alias.asname or alias.name] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module == "flask":
                for alias in node.names:
                    if alias.name == "request":
                        imports[alias.asname or alias.name] = "flask.request"
        # A rebound import is not a known API. This conservative global filter also
        # covers parameter shadowing and assignment later in a function.
        rebound = {
            n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        }
        rebound |= {n.arg for n in ast.walk(tree) if isinstance(n, ast.arg)}
        imports = {k: v for k, v in imports.items() if k not in rebound}

        def qualified(node: ast.AST) -> str:
            if isinstance(node, ast.Name):
                return imports.get(node.id, "")
            if isinstance(node, ast.Attribute):
                return qualified(node.value) + "." + node.attr
            return ""

        for function in tree.body:
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not all(n in rows for n in range(1, (function.end_lineno or 0) + 1)):
                continue
            tainted: dict[str, int] = {}

            def origin(node: ast.AST) -> int | None:
                if isinstance(node, ast.Name):
                    return tainted.get(node.id)
                if isinstance(node, ast.Call) and qualified(node.func) in {
                    "flask.request.args.get",
                    "flask.request.form.get",
                }:
                    return node.lineno
                if isinstance(node, ast.Subscript) and qualified(node.value) in {
                    "flask.request.args",
                    "flask.request.form",
                }:
                    return node.lineno
                return None

            for stmt in function.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                    target = stmt.targets[0]
                    if isinstance(target, ast.Name):
                        value = origin(stmt.value)
                        tainted.pop(target.id, None)
                        if value is not None:
                            tainted[target.id] = value
                call = stmt.value if isinstance(stmt, (ast.Expr, ast.Return, ast.Assign)) else None
                if isinstance(call, ast.Call) and call.args:
                    name = qualified(call.func)
                    sink = name == "os.system" or (
                        name in {"subprocess.run", "subprocess.call", "subprocess.Popen"}
                        and any(
                            k.arg == "shell"
                            and isinstance(k.value, ast.Constant)
                            and k.value.value is True
                            for k in call.keywords
                        )
                    )
                    start = origin(call.args[0])
                    evidence = (
                        list(range(start, (call.end_lineno or call.lineno) + 1)) if start else []
                    )
                    # Missing lines, control-flow joins, transformations and unknown
                    # calls are not interpreted as proven taint propagation.
                    if (
                        sink
                        and start
                        and len(evidence) <= 40
                        and all(n in rows for n in evidence)
                        and any(rows[n]["changed"] for n in evidence)
                    ):
                        findings.append(
                            {
                                "rule_id": "PY-INPUT-SHELL-1",
                                "file_id": file["file_id"],
                                "line": call.lineno,
                                "source_line": start,
                                "evidence_lines": evidence,
                                "severity": "WARNING",
                                "title": "웹 요청 값이 셸 명령으로 직접 전달돼요",
                                "detail": "제공된 직선 실행 구간에서 요청 값이 셸까지 전달됩니다. "
                                "전체 경로의 접근 가능성과 앞단 정책은 확인하지 않았어요.",
                            }
                        )
                if not isinstance(stmt, (ast.Assign, ast.Expr)):
                    break
                # Unknown calls may mutate state or enforce a guard; stop propagation.
                if isinstance(call, ast.Call) and not qualified(call.func).startswith(
                    "flask.request."
                ):
                    tainted.clear()
                if len(findings) >= 10:
                    return findings
    return findings
