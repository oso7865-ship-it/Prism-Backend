"""Isolated syntax metadata only; repository source is never imported or persisted."""

import json
import re
import sys

from tree_sitter import Language, Parser


def metadata(path: str, source: str) -> dict[str, object]:
    import tree_sitter_java
    import tree_sitter_javascript
    import tree_sitter_python
    import tree_sitter_typescript

    factories = {
        "java": tree_sitter_java.language,
        "py": tree_sitter_python.language,
        "js": tree_sitter_javascript.language,
        "jsx": tree_sitter_javascript.language,
        "ts": tree_sitter_typescript.language_typescript,
        "tsx": tree_sitter_typescript.language_tsx,
    }
    raw = source.encode()
    if len(raw) > 200_000:
        raise ValueError("SOURCE_LIMIT")
    tree = Parser(Language(factories[path.rsplit(".", 1)[-1]]())).parse(raw)
    spans: list[list[int | str]] = []
    names: set[str] = set()
    imports: list[str] = []
    calls: list[list[int | str]] = []
    symbols: list[list[int | str]] = []
    stack, visited = [tree.root_node], 0
    definitions = {
        "function_definition",
        "function_declaration",
        "method_declaration",
        "method_definition",
        "constructor_declaration",
        "arrow_function",
        "function_expression",
    }
    while stack and visited < 100_000:
        node = stack.pop()
        visited += 1
        if node.type in definitions and len(spans) < 128:
            name = node.child_by_field_name("name")
            if name is None and node.parent is not None:
                name = node.parent.child_by_field_name("name")
            label = raw[name.start_byte : name.end_byte].decode()[:128] if name else ""
            start = node.start_point.row + 1
            if node.parent and node.parent.type == "decorated_definition":
                start = node.parent.start_point.row + 1
            spans.append([start, node.end_point.row + 1, label])
        if node.type in {"identifier", "type_identifier", "property_identifier"}:
            label = raw[node.start_byte : node.end_byte].decode()
            if len(names) < 256 and re.fullmatch(r"[A-Za-z_$][\w$]{1,127}", label):
                names.add(label)
                if len(symbols) < 2048:
                    symbols.append([node.start_point.row + 1, label])
        if node.type in {"call", "call_expression", "method_invocation"} and len(calls) < 256:
            target = node.child_by_field_name("name") or node.child_by_field_name("function")
            if target is not None:
                target = (
                    target.child_by_field_name("attribute")
                    or target.child_by_field_name("property")
                    or target
                )
                label = raw[target.start_byte : target.end_byte].decode()
                if re.fullmatch(r"[A-Za-z_$][\w$]{0,127}", label):
                    calls.append([node.start_point.row + 1, label])
        if (
            node.type
            in {
                "import_declaration",
                "import_statement",
                "import_from_statement",
            }
            and len(imports) < 40
        ):
            imports.append(raw[node.start_byte : node.end_byte].decode()[:500])
        stack.extend(reversed(node.named_children))
    return {
        "spans": spans,
        "identifiers": sorted(names),
        "imports": imports,
        "calls": calls,
        "symbols": symbols,
        "partial": (
            tree.root_node.has_error
            or bool(stack)
            or len(spans) == 128
            or len(names) == 256
            or len(imports) == 40
            or len(calls) == 256
            or len(symbols) == 2048
        ),
    }


if __name__ == "__main__":
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    request = json.loads(sys.stdin.buffer.read(16_000_001))
    if not isinstance(request, dict) or len(request) > 12:
        raise ValueError("BATCH_LIMIT")
    print(json.dumps({path: metadata(path, code) for path, code in request.items()}))
