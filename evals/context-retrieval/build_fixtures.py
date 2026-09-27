"""Deterministic synthetic cross-file corpus, frozen before model measurements."""

# Source fixture literals retain their exact formatting for review evaluation.
# ruff: noqa: E501

import json
from pathlib import Path


def make(language, variant):
    ext = {"python": "py", "java": "java", "javascript": "js", "typescript": "ts"}[language]
    negative = variant == "guarded-null"
    name = {"guarded-null": "requireUser", "nullable-user": "findUser", "zero-count": "itemCount"}[
        variant
    ]
    if language == "python":
        main = f"from account_store import {name}\n\ndef label(value):\n" + (
            f"    return 100 / {name}(value)"
            if variant == "zero-count"
            else f"    return {name}(value).name"
        )
        if negative:
            helper = "def requireUser(value):\n    if value is None:\n        raise ValueError('missing')\n    return value"
        elif variant == "nullable-user":
            helper = "def findUser(value):\n    if value == 0:\n        return None\n    return type('User', (), {'name': 'Ada'})()"
        else:
            helper = "def itemCount(value):\n    return len(value)"
        support, changed = "src/account_store.py", "src/account_label.py"
        expected = [] if negative else [4]
        filler = "# Unrelated account module documentation\n" * 100
        noise = "def accountTelemetry(value):\n    return {'account': str(value)}"
    elif language == "java":
        main = (
            "import sample.AccountStore;\nclass AccountLabel {\n  String label(int value) {\n"
            + (
                f"    return Integer.toString(100 / AccountStore.{name}(value));"
                if variant == "zero-count"
                else f"    return AccountStore.{name}(value).trim();"
            )
            + "\n  }\n}"
        )
        if negative:
            helper = '  static String requireUser(int value) {\n    if (value == 0) throw new IllegalArgumentException();\n    return "Ada";\n  }'
        elif variant == "nullable-user":
            helper = '  static String findUser(int value) {\n    if (value == 0) return null;\n    return "Ada";\n  }'
        else:
            helper = "  static int itemCount(int value) {\n    return value == 0 ? 0 : 2;\n  }"
        support, changed = "src/sample/AccountStore.java", "src/sample/AccountLabel.java"
        expected = [] if negative else [4]
        filler = (
            "package sample;\nclass AccountStore {\n"
            + "// Unrelated account module documentation\n" * 100
        )
        helper += "\n}"
        noise = "class AccountTelemetry { static String accountTelemetry(int value) { return Integer.toString(value); } }"
    else:
        typed = language == "typescript"
        arg = "value: number" if typed else "value"
        main = (
            f"import {{ {name} }} from './accountStore';\nexport function label({arg}) {{\n"
            + (
                f"  return (100 / {name}(value)).toFixed();"
                if variant == "zero-count"
                else f"  return {name}(value).name;"
            )
            + "\n}"
        )
        if negative:
            helper = f"export function requireUser({arg}) {{\n  if (value === 0) throw new Error('missing');\n  return {{name: 'Ada'}};\n}}"
        elif variant == "nullable-user":
            helper = f"export function findUser({arg}) {{\n  if (value === 0) return null;\n  return {{name: 'Ada'}};\n}}"
        else:
            # Explicit contract prevents treating JavaScript Infinity as a thrown exception.
            main = (
                f"import {{ itemCount }} from './accountStore';\nexport function allocate({arg}) {{\n"
                "  return new Array(itemCount(value));\n}"
            )
            helper = f"export function itemCount({arg}) {{\n  return value === 0 ? -1 : 2;\n}}"
        support, changed = f"src/accountStore.{ext}", f"src/accountLabel.{ext}"
        expected = [] if negative else [3]
        filler = "// Unrelated account module documentation\n" * 100
        noise = f"export function accountTelemetry({arg}) {{ return String(value); }}"
    files = {changed: main, support: filler + helper}
    for suffix in ("Cache", "Metrics", "Policy"):
        files[f"src/account{suffix}.{ext}"] = noise
    first = len(filler.splitlines()) + 1
    return {
        "id": f"{language}-{variant}",
        "path": changed,
        "patch": f"@@ -0,0 +1,{len(main.splitlines())} @@\n"
        + "\n".join("+" + line for line in main.splitlines()),
        "files": files,
        "required_context": {
            "path": support,
            "lines": list(range(first, first + len(helper.splitlines()) - (language == "java"))),
        },
        "expected_lines": expected,
        "rubric": "Do not invent missing caller contracts. Trace the supplied helper return/throw into the changed operation. JS/TS negative array length raises RangeError; do not claim Python exceptions there.",
    }


if __name__ == "__main__":
    cases = [
        make(lang, variant)
        for lang in ("python", "java", "javascript", "typescript")
        for variant in ("guarded-null", "nullable-user", "zero-count")
    ]
    Path(__file__).with_name("cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
