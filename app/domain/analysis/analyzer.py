"""Pure syntax evaluation. No imports or execution of customer code."""

import re

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
