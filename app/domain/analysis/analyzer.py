"""Pure syntax evaluation. No imports or execution of customer code."""

import re
from collections.abc import Callable

from tree_sitter import Language, Node, Parser

from app.domain.analysis.contracts import (
    MAX_FILE,
    Evaluation,
    Observation,
    applicable,
    language_for,
)


def parser_for(language: str, path: str) -> Parser:
    import tree_sitter_java
    import tree_sitter_javascript
    import tree_sitter_python
    import tree_sitter_typescript

    capsules = {
        "JAVA": tree_sitter_java.language,
        "PYTHON": tree_sitter_python.language,
        "JAVASCRIPT": tree_sitter_javascript.language,
        "TYPESCRIPT": tree_sitter_typescript.language_tsx
        if path.endswith(".tsx")
        else tree_sitter_typescript.language_typescript,
    }
    return Parser(Language(capsules[language]()))


def evaluate(path: str, source: bytes, ignored: bool = False) -> Evaluation:
    language = language_for(path)
    out = Evaluation(language=language, status="INCLUDED")
    if len(source) > MAX_FILE:
        return Evaluation(language=language, status="LIMIT_EXCEEDED", reason="FILE_SIZE_LIMIT")
    try:
        content = source.decode("utf-8")
    except UnicodeDecodeError:
        return Evaluation(language=language, status="EXCLUDED", reason="ENCODING_UNSUPPORTED")
    if "\x00" in content or content.startswith("version https://git-lfs.github.com/spec/v1"):
        return Evaluation(language=language, status="EXCLUDED", reason="BINARY_OR_LFS")
    seen: set[tuple[str, int, int]] = set()

    def add(rule: str, start: int, end: int) -> None:
        key = (rule, start, end)
        if key in seen:
            return
        seen.add(key)
        if len(out.findings) >= 100:
            out.limit = True
        else:
            out.findings.append(Observation(rule_id=rule, start_line=start, end_line=end))

    key_ranges: list[tuple[int, int]] = []
    for match in re.finditer(
        (
            "-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
            "[\\s\\S]*?-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KE"
            "Y-----"
        ),
        content,
    ):
        start, end = (
            content.count("\n", 0, match.start()) + 1,
            content.count("\n", 0, match.end()) + 1,
        )
        key_ranges.append((start, end))
        add("COM-010", start, end)
    for match in re.finditer(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}|AKIA[A-Z0-9]{16})\b", content
    ):
        line = content.count("\n", 0, match.start()) + 1
        if not any(a <= line <= b for a, b in key_ranges):
            add("COM-009", line, line)
    out.evaluated = ["COM-009", "COM-010"]
    if not language or ignored or path.endswith((".d.ts", ".d.mts", ".d.cts")):
        out.reason = "SECRET_SCAN_ONLY" if not ignored else "IGNORED_SOURCE_RULES"
        return out
    if path.endswith((".min.js", ".min.css")) or "@generated" in content[:1000]:
        out.reason = "GENERATED_SECRET_SCAN_ONLY"
        return out
    tree = parser_for(language, path).parse(source)
    structural = [r for r in applicable(language) if r not in out.evaluated]
    if tree.root_node.has_error:
        out.status, out.reason, out.not_evaluated = "PARSE_ERROR", "SYNTAX_ERROR", structural
        return out
    out.evaluated.extend(structural)
    lines = len(content.splitlines())
    if lines > 500:
        add("COM-001", 1, lines)

    def node_add(rule: str, node: Node) -> None:
        add(
            rule, node.start_point.row + 1, node.end_point.row + (1 if node.end_point.column else 0)
        )

    def text_of(node: Node | None) -> str:
        return (node.text or b"").decode("utf-8") if node else ""

    def empty_body(node: Node | None) -> bool:
        return node is not None and not [
            c
            for c in node.named_children
            if c.type not in ("comment", "line_comment", "block_comment")
        ]

    evaluate_additional(tree.root_node, language, node_add, out)
    if out.not_evaluated:
        out.reason = "BINDING_UNRESOLVED"

    stack = [tree.root_node]
    while stack:
        n = stack.pop()
        stack.extend(reversed(n.named_children))
        t = n.type
        if t in (
            "function_definition",
            "method_declaration",
            "constructor_declaration",
            "function_declaration",
            "generator_function_declaration",
            "function_expression",
            "generator_function",
            "arrow_function",
            "method_definition",
        ):
            if n.end_point.row - n.start_point.row + 1 > 60:
                node_add("COM-002", n)
            params = n.child_by_field_name("parameters") or n.child_by_field_name("parameter")
            if params:
                values = [
                    c for c in params.named_children if c.type not in ("comment", "type_parameters")
                ]
                if language == "PYTHON":
                    values = [
                        c
                        for c in values
                        if c.type not in ("positional_separator", "keyword_separator")
                        and text_of(c) not in ("self", "cls")
                    ]
                if len(values) > 5:
                    node_add("COM-004", n)
        if language == "JAVA":
            if t == "catch_clause" and empty_body(n.child_by_field_name("body")):
                node_add("JAVA-004", n)
            if t == "import_declaration" and any(c.type == "asterisk" for c in n.named_children):
                node_add("JAVA-005", n)
            if t in ("for_statement", "enhanced_for_statement", "while_statement", "do_statement"):
                body = n.child_by_field_name("body")
                if body and body.type == ";":
                    node_add("JAVA-006", n)
            if t == "field_declaration":
                mods = next((c for c in n.children if c.type == "modifiers"), None)
                types = {c.type for c in mods.children} if mods else set()
                if {"public", "static"} <= types and "final" not in types:
                    node_add("JAVA-007", n)
            if t == "binary_expression" and text_of(n.child_by_field_name("operator")) in (
                "==",
                "!=",
            ):
                if any(c.type == "string_literal" for c in n.named_children):
                    node_add("JAVA-008", n)
        if language == "PYTHON":
            if t in ("default_parameter", "typed_default_parameter"):
                v = n.child_by_field_name("value")
                if v and v.type in ("list", "dictionary", "set"):
                    node_add("PY-001", n)
            if t == "except_clause":
                body = next((c for c in n.named_children if c.type == "block"), None)
                typed = [c for c in n.named_children if c.type not in ("block", "comment")]
                if not typed:
                    node_add("PY-002", n)
                elif body and all(
                    c.type in ("pass_statement", "comment") for c in body.named_children
                ):
                    node_add("PY-003", n)
            if t == "import_from_statement" and any(
                c.type == "wildcard_import" for c in n.named_children
            ):
                node_add("PY-006", n)
        if language in ("JAVASCRIPT", "TYPESCRIPT"):
            if t == "variable_declaration":
                node_add("JS-001", n)
            if t == "debugger_statement":
                node_add("JS-003", n)
            if t == "catch_clause" and empty_body(n.child_by_field_name("body")):
                node_add("JS-004", n)
            if (
                t == "binary_expression"
                and text_of(n.child_by_field_name("operator")) in ("==", "!=")
                and not any(c.type == "null" for c in n.named_children)
            ):
                node_add("JS-002", n)
        if language == "TYPESCRIPT":
            if t == "predefined_type" and text_of(n) == "any":
                node_add("TS-001", n)
            if t == "comment":
                for directive, rule in [("ignore", "TS-002"), ("nocheck", "TS-003")]:
                    if re.match(r"^\s*(?:///?|/\*+)\s*@ts-" + directive + r"\b", text_of(n)):
                        node_add(rule, n)
            if t == "non_null_expression":
                node_add("TS-004", n)
            if (
                t == "as_expression"
                and n.named_children
                and n.named_children[0].type == "as_expression"
            ):
                inner = n.named_children[0]
                if inner.named_children and text_of(inner.named_children[-1]) in ("any", "unknown"):
                    node_add("TS-005", n)
    return out


def evaluate_additional(
    root: Node, language: str, emit: Callable[[str, Node], None], out: Evaluation
) -> None:
    """Bounded syntax checks; uncertain binding makes the whole rule unevaluated."""
    functions = {
        "function_definition",
        "method_declaration",
        "constructor_declaration",
        "function_declaration",
        "generator_function_declaration",
        "function_expression",
        "generator_function",
        "arrow_function",
        "method_definition",
        "lambda_expression",
        "lambda",
    }
    controls = {
        "if_statement",
        "elif_clause",
        "for_statement",
        "for_in_statement",
        "enhanced_for_statement",
        "while_statement",
        "do_statement",
    }
    nodes: list[Node] = []
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        nodes.append(node)
        if node.type in functions:
            depth = 0
        if node.type in controls:
            # Python elif and the JS/Java else-if syntax do not add another nesting level.
            parent = node.parent
            chained = node.type == "elif_clause" or (
                node.type == "if_statement"
                and parent is not None
                and (
                    parent.type == "else_clause"
                    or (
                        parent.type == "if_statement"
                        and parent.child_by_field_name("alternative") == node
                    )
                )
            )
            if not chained:
                depth += 1
            if depth == 5 and not chained:
                emit("COM-003", node)
        stack.extend((child, depth) for child in reversed(node.named_children))

    def text(node: Node | None) -> str:
        return (node.text or b"").decode("utf-8") if node else ""

    def unbound(name: str, allowed: set[str]) -> bool:
        for node in nodes:
            if language == "PYTHON" and node.type == "wildcard_import":
                return False
            if node.type == "with_statement" and language != "PYTHON":
                return False
            if node.type == "property_identifier" and text(node) == name:
                return False
            if (
                node.type
                not in (
                    "identifier",
                    "type_identifier",
                    "shorthand_property_identifier_pattern",
                    "shorthand_property_identifier",
                )
                or text(node) != name
            ):
                continue
            parent = node.parent
            if parent is None or parent.type not in allowed:
                return False
            if parent.type in ("call", "call_expression", "new_expression"):
                field = "constructor" if parent.type == "new_expression" else "function"
                if parent.child_by_field_name(field) != node:
                    return False
        return True

    targets = (
        [("eval", "PY-004"), ("exec", "PY-005")]
        if language == "PYTHON"
        else [("eval", "JS-005"), ("Function", "JS-006")]
        if language in ("JAVASCRIPT", "TYPESCRIPT")
        else []
    )
    for name, rule in targets:
        allowed = {"call"} if language == "PYTHON" else {"call_expression"}
        if name == "Function":
            allowed.add("new_expression")
        dynamic = any(
            (
                node.type == "call"
                and text(node.child_by_field_name("function"))
                in ("globals", "locals", "vars", "setattr", "__import__")
            )
            or (
                node.type == "identifier"
                and text(node) in ("globalThis", "window", "global", "builtins", "__builtins__")
            )
            or (
                name != "exec"
                and node.type == "call"
                and text(node.child_by_field_name("function")) == "exec"
            )
            or (
                name != "eval"
                and node.type == "call_expression"
                and text(node.child_by_field_name("function")) == "eval"
            )
            for node in nodes
        )
        if not unbound(name, allowed) or dynamic:
            out.evaluated.remove(rule)
            out.not_evaluated.append(rule)
            continue
        for node in nodes:
            if node.type in allowed:
                field = "constructor" if node.type == "new_expression" else "function"
                callee = node.child_by_field_name(field)
                if callee and callee.type == "identifier" and text(callee) == name:
                    emit(rule, node)
    if language == "PYTHON":
        if not all(
            unbound(name, {"except_clause", "as_pattern", "tuple"})
            for name in ("Exception", "BaseException")
        ):
            out.evaluated.remove("PY-008")
            out.not_evaluated.append("PY-008")
            return
        for node in nodes:
            if node.type != "except_clause":
                continue
            body = next((child for child in node.named_children if child.type == "block"), None)
            if body and all(
                child.type in ("pass_statement", "comment") for child in body.named_children
            ):
                continue
            value = node.child_by_field_name("value")
            if value and value.type == "as_pattern":
                value = value.named_children[0]
            values = value.named_children if value and value.type == "tuple" else [value]
            if any(
                v and v.type == "identifier" and text(v) in ("Exception", "BaseException")
                for v in values
            ):
                emit("PY-008", node)
