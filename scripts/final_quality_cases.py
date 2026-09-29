"""New authored contract counterfactuals; never execute the source strings."""

# ruff: noqa: E501 -- Auditable fixture source and requirements.
from scripts.quality_lab_protocol import digest


def cases():
    pairs = [
        (
            "copy-py",
            "snapshot.py",
            "settings contains a plain limits dictionary with integer cap. Leave the caller's nested state unchanged. No return-value requirement is specified.",
            "def adjust(settings):\n    scratch = settings.copy()\n    scratch['limits']['cap'] = 12\n    return settings['limits']['cap']",
            "def adjust(settings):\n    scratch = {**settings, 'limits': settings['limits'].copy()}\n    scratch['limits']['cap'] = 12\n    return settings['limits']['cap']",
            [2, 3],
        ),
        (
            "copy-js",
            "scratch.js",
            "values is an array of finite numbers. Do not modify the caller's array; no return-order requirement is specified.",
            "function inspect(values) {\n  const scratch = values;\n  scratch.sort((a,b) => a-b);\n  return values;\n}",
            "function inspect(values) {\n  const scratch = values.slice();\n  scratch.sort((a,b) => a-b);\n  return values;\n}",
            [2, 3],
        ),
        (
            "copy-ts",
            "profile.ts",
            "settings.limits.cap is a number. Leave the caller's nested state unchanged; no return-value requirement is specified.",
            "function inspect(settings: {limits: {cap: number}}) {\n  const scratch = {...settings};\n  scratch.limits.cap = 12;\n  return settings.limits.cap;\n}",
            "function inspect(settings: {limits: {cap: number}}) {\n  const scratch = {...settings, limits: {...settings.limits}};\n  scratch.limits.cap = 12;\n  return settings.limits.cap;\n}",
            [2, 3],
        ),
        (
            "copy-java",
            "Scratch.java",
            "values is a non-null nonempty int array. Do not mutate the caller's array; no return-value requirement is specified.",
            "class Scratch {\n  int inspect(int[] values) {\n    int[] scratch = values;\n    scratch[0] = 12;\n    return values[0];\n  }\n}",
            "class Scratch {\n  int inspect(int[] values) {\n    int[] scratch = values.clone();\n    scratch[0] = 12;\n    return values[0];\n  }\n}",
            [3, 4],
        ),
        (
            "zero-default",
            "retries.py",
            "value is None or a nonnegative int. Preserve explicit zero; use 5 only for None.",
            "def retries(value):\n    return value or 5",
            "def retries(value):\n    return 5 if value is None else value",
            [2],
        ),
        (
            "await-check",
            "access.js",
            "check returns a Promise<boolean>. Return the same authorization decision after it resolves.",
            "async function allowed(check, user) {\n  if (check(user)) return true;\n  return false;\n}",
            "async function allowed(check, user) {\n  if (await check(user)) return true;\n  return false;\n}",
            [2],
        ),
        (
            "null-guard",
            "length.ts",
            "For null return zero, otherwise return string length.",
            "function size(value: string | null): number {\n  if (value === null && value.length === 0) return 0;\n  return value.length;\n}",
            "function size(value: string | null): number {\n  if (value === null || value.length === 0) return 0;\n  return value.length;\n}",
            [2, 3],
        ),
        (
            "java-index",
            "Tail.java",
            "values is a non-null, nonempty int array. Return its final element.",
            "class Tail {\n  int read(int[] values) {\n    return values[values.length];\n  }\n}",
            "class Tail {\n  int read(int[] values) {\n    return values[values.length - 1];\n  }\n}",
            [3],
        ),
    ]
    result = []

    def add(family, path, contract, source, fixed, locations):
        result.append(
            {
                "id": digest("final:" + family + str(fixed))[:12],
                "family": family,
                "fixed": fixed,
                "path": path,
                "source": source,
                "previous_source": "",
                "contract": contract,
                "extra": "",
                "purpose": "CODE",
                "document": None,
                "changed_lines": list(range(1, len(source.splitlines()) + 1)),
                "expected_lines": [] if fixed else locations,
                "probes": [],
                "oracle": [],
            }
        )

    for family, path, contract, bad, good, lines in pairs:
        add(family, path, contract, bad, False, lines)
        add(family, path, contract, good, True, lines)

    # Identical source, opposite explicit requirements: no name-based special casing.
    counterfactuals = [
        (
            "contract-py",
            "adjusted.py",
            "def adjust(value):\n    adjusted = max(value, 0)\n    return value",
            "value is an int. Return max(value, 0).",
            "value is an int. Return the original value unchanged, including negatives.",
            [3],
        ),
        (
            "contract-js",
            "trim.js",
            "function trim(value) {\n  const trimmed = value.trim();\n  return value;\n}",
            "value is a string. Return its text with leading and trailing whitespace removed.",
            "value is a string. Return its original text including all whitespace.",
            [3],
        ),
        (
            "contract-ts",
            "scale.ts",
            "function scale(value: number): number {\n  const scaled = value * 2;\n  return value;\n}",
            "value is a finite number with absolute value below 100. Return double the input.",
            "value is a finite number with absolute value below 100. Return the input unchanged.",
            [3],
        ),
        (
            "contract-java",
            "Normalize.java",
            "class Normalize {\n  int normalize(int value) {\n    int adjusted = Math.max(value, 0);\n    return value;\n  }\n}",
            "For every int value return Math.max(value, 0).",
            "For every int value return that original value, including negatives.",
            [4],
        ),
    ]
    for family, path, source, bad_contract, good_contract, lines in counterfactuals:
        add(family, path, bad_contract, source, False, lines)
        add(family, path, good_contract, source, True, lines)
    return result
