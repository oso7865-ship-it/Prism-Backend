"""Trusted authored fixtures. Source strings are data: never execute or import them."""

# ruff: noqa: E501 -- Preserve authored source/contract strings as auditable fixture data.

import hashlib
import json
from pathlib import Path


def value(item):
    return {
        "outcome": "RETURN",
        "value_json": json.dumps(item, ensure_ascii=False),
        "exception_type": None,
    }


def raises(name):
    return {"outcome": "RAISE", "value_json": None, "exception_type": name}


def family(
    name,
    path,
    bad,
    good,
    lines,
    contract,
    calls,
    bad_values,
    good_values,
    *,
    extra="",
    purpose="CODE",
    document=None,
):
    return dict(
        name=name,
        path=path,
        bad=bad,
        good=good,
        lines=lines,
        contract=contract,
        calls=calls,
        bad_values=bad_values,
        good_values=good_values,
        extra=extra,
        purpose=purpose,
        document=document,
    )


def discovery():
    return [
        family(
            "explicit-value",
            "settings.py",
            "def choose(value, default):\n    return value or default",
            "def choose(value, default):\n    return default if value is None else value",
            [2],
            "Only None means absent. Preserve all explicitly provided values.",
            ["choose('', 'default')", "choose(False, True)", "choose(None, 'default')"],
            [value("default"), value(True), value("default")],
            [value(""), value(False), value("default")],
        ),
        family(
            "utf8-length",
            "wire.py",
            "def wire_size(body):\n    return len(body)",
            "def wire_size(body):\n    return len(body.encode('utf-8') if isinstance(body, str) else body)",
            [2],
            "Accept str or bytes; return the number of bytes sent on the wire using UTF-8.",
            ["wire_size('한글')", "wire_size(b'AB')", "wire_size('')"],
            [value(2), value(2), value(0)],
            [value(6), value(2), value(0)],
        ),
        family(
            "zero-step",
            "indices.py",
            "def indices(n):\n    return list(range(0, n, n))",
            "def indices(n):\n    return list(range(0, n, max(n, 1)))",
            [2],
            "n is a nonnegative int. Return [] for n=0 and [0] for a positive n.",
            ["indices(0)", "indices(3)"],
            [raises("ValueError"), value([0])],
            [value([]), value([0])],
        ),
        family(
            "mutable-default",
            "collector.py",
            "def collect(item, bucket=[]):\n    bucket.append(item)\n    return bucket",
            "def collect(item, bucket=None):\n    if bucket is None:\n        bucket = []\n    bucket.append(item)\n    return bucket",
            [1, 2, 3],
            "Each omitted-bucket call gets a fresh bucket. Explicit buckets are modified in place.",
            [
                "Fresh module: copy collect(1), then copy collect(2); return the two snapshots.",
                "Fresh module: collect(3, [9])",
            ],
            [value([[1], [1, 2]]), value([9, 3])],
            [value([[1], [2]]), value([9, 3])],
        ),
        family(
            "int-overflow",
            "Price.java",
            "class Price {\n  static long total(int amount, int count) {\n    return amount * count;\n  }\n}",
            "class Price {\n  static long total(int amount, int count) {\n    return (long) amount * count;\n  }\n}",
            [3],
            "Both inputs are nonnegative int values; the exact product fits in long and must be preserved.",
            ["Price.total(50000, 50000)", "Price.total(2, 3)"],
            [value(-1794967296), value(6)],
            [value(2500000000), value(6)],
        ),
        family(
            "null-branch",
            "Display.java",
            'class Display {\n  static String name(String name) {\n    return name == null ? name.trim() : "";\n  }\n}',
            'class Display {\n  static String name(String name) {\n    return name == null ? "" : name.trim();\n  }\n}',
            [3],
            "A null name is displayed as empty; otherwise strip surrounding whitespace.",
            ["Display.name(null)", 'Display.name(" Ada ")'],
            [raises("NullPointerException"), value("")],
            [value(""), value("Ada")],
        ),
        family(
            "zero-count",
            "limits.js",
            "function limit(count) {\n  return count || 10;\n}",
            "function limit(count) {\n  return count ?? 10;\n}",
            [2],
            "Use default 10 only for null or undefined; zero is a valid configured limit.",
            ["limit(0)", "limit(null)", "limit(5)"],
            [value(10), value(10), value(5)],
            [value(0), value(10), value(5)],
        ),
        family(
            "ownership",
            "invoice.ts",
            "function invoice(id: number, actor: string) {\n  const item = load(id);\n  return item.amount;\n}",
            'function invoice(id: number, actor: string) {\n  const item = load(id);\n  if (item.owner !== actor) throw new Error("denied");\n  return item.amount;\n}',
            [2, 3, 4],
            "Return the amount only to its owner; throw Error for other actors. id=7 exists.",
            ['invoice(7, "bob")', 'invoice(7, "alice")'],
            [value(40), value(40)],
            [raises("Error"), value(40)],
            extra='function load(id: number) { return {owner: "alice", amount: 40}; }',
            purpose="SECURITY",
        ),
        family(
            "path-boundary",
            "paths.py",
            "def permitted(root, resolved):\n    return resolved.startswith(root)",
            "def permitted(root, resolved):\n    return resolved == root or resolved.startswith(root + '/')",
            [2],
            "Inputs are canonical absolute POSIX paths without symlinks or trailing slash. Only root and its descendants are allowed.",
            [
                "permitted('/srv/app', '/srv/application/key')",
                "permitted('/srv/app', '/srv/app/file')",
            ],
            [value(True), value(True)],
            [value(False), value(True)],
            purpose="SECURITY",
        ),
        family(
            "logging-standard",
            "app/service.py",
            "def save(record, logger):\n    print('saved')\n    return record",
            "def save(record, logger):\n    logger.info('saved')\n    return record",
            [2],
            "record is any value. logger.info exists and has no return value or side effects beyond logging.",
            ["save(7, logger), observe return value only"],
            [value(7)],
            [value(7)],
            purpose="STANDARDS",
            document="# 로깅\n애플리케이션에서는 print 대신 주입된 logger.info로 기록한다.",
        ),
    ]


def holdout():
    return [
        family(
            "empty-mean",
            "mean.py",
            "def mean(values):\n    return sum(values) / len(values)",
            "def mean(values):\n    return sum(values) / len(values) if values else 0.0",
            [2],
            "Finite numeric lists only. Empty input has mean 0.0 by this API contract.",
            ["mean([])", "mean([2, 4])"],
            [raises("ZeroDivisionError"), value(3.0)],
            [value(0.0), value(3.0)],
        ),
        family(
            "late-binding",
            "callbacks.py",
            "def callbacks():\n    return [lambda: i for i in range(3)]",
            "def callbacks():\n    return [lambda i=i: i for i in range(3)]",
            [2],
            "Each callback returns the index captured when it was created.",
            ["[fn() for fn in callbacks()]"],
            [value([2, 2, 2])],
            [value([0, 1, 2])],
        ),
        family(
            "nested-copy",
            "options.py",
            "def adjust(base):\n    result = base.copy()\n    result['nested']['limit'] = 9\n    return base['nested']['limit']",
            "def adjust(base):\n    result = {**base, 'nested': base['nested'].copy()}\n    result['nested']['limit'] = 9\n    return base['nested']['limit']",
            [2],
            "base has a nested dictionary. Preserve the caller's base without mutation.",
            ["adjust({'nested': {'limit': 1}})"],
            [value(9)],
            [value(1)],
        ),
        family(
            "comparator-overflow",
            "Order.java",
            "class Order {\n  static int compare(int left, int right) {\n    return left - right;\n  }\n}",
            "class Order {\n  static int compare(int left, int right) {\n    return Integer.compare(left, right);\n  }\n}",
            [3],
            "A comparator must have negative sign when left < right, zero on equality, positive otherwise.",
            [
                "Integer.signum(Order.compare(Integer.MIN_VALUE, 1))",
                "Integer.signum(Order.compare(3, 3))",
            ],
            [value(1), value(0)],
            [value(-1), value(0)],
        ),
        family(
            "async-guard",
            "access.js",
            "async function access(check) {\n  if (check()) return 'allowed';\n  return 'denied';\n}",
            "async function access(check) {\n  if (await check()) return 'allowed';\n  return 'denied';\n}",
            [2],
            "check is async and resolves to a boolean. Allow only when it resolves true.",
            ["await access(async () => false)", "await access(async () => true)"],
            [value("allowed"), value("allowed")],
            [value("denied"), value("allowed")],
            purpose="SECURITY",
        ),
        family(
            "optional-chain",
            "profile.ts",
            "type User = { profile?: { name: string } };\nfunction name(user: User) {\n  return user.profile!.name;\n}",
            "type User = { profile?: { name: string } };\nfunction name(user: User) {\n  return user.profile?.name ?? 'Unknown';\n}",
            [3],
            "user exists. Missing profile must display Unknown; an existing empty name is preserved.",
            ["name({})", 'name({profile: {name: ""}})'],
            [raises("TypeError"), value("")],
            [value("Unknown"), value("")],
        ),
        family(
            "sql-binding",
            "query.py",
            "def query(user_id):\n    return ('SELECT name FROM users WHERE id = ' + user_id, ())",
            "def query(user_id):\n    return ('SELECT name FROM users WHERE id = %s', (user_id,))",
            [2],
            "Caller passes the returned SQL and parameter tuple directly to a DB-API driver using %s placeholders. user_id is untrusted text.",
            ["query('0 OR 1=1'), JSON encode the returned tuple as an array"],
            [value(["SELECT name FROM users WHERE id = 0 OR 1=1", []])],
            [value(["SELECT name FROM users WHERE id = %s", ["0 OR 1=1"]])],
            purpose="SECURITY",
        ),
        family(
            "error-standard",
            "app/handler.py",
            "def handle(operation, logger):\n    try:\n        return operation()\n    except ValueError:\n        return None",
            "def handle(operation, logger):\n    try:\n        return operation()\n    except ValueError:\n        logger.error('failed')\n        raise",
            [4, 5, 6],
            "operation raises ValueError for the supplied probe; logger.error returns normally.",
            ["handle(operation, logger) with operation raising ValueError"],
            [value(None)],
            [raises("ValueError")],
            purpose="STANDARDS",
            document="# 오류 처리\n입력 오류는 호출자가 처리하도록 기록한 뒤 같은 예외를 다시 던진다. 실패를 정상 반환으로 숨기지 않는다.",
        ),
    ]


def generate():
    cases = []
    for split, families in [("development", discovery()), ("holdout", holdout())]:
        for family_index, f in enumerate(families):
            for fixed in [False, True]:
                source = f["good" if fixed else "bad"]
                # Opaque IDs and allowlisted payload fields prevent filename/label leakage.
                identity = hashlib.sha256(f"{split}:{family_index}:{fixed}".encode()).hexdigest()[
                    :12
                ]
                observations = f["good_values" if fixed else "bad_values"]
                cases.append(
                    {
                        "id": identity,
                        "split": split,
                        "family": f["name"],
                        "fixed": fixed,
                        "path": f["path"],
                        "source": source,
                        "previous_source": f["bad" if fixed else "good"],
                        "changed_lines": [n for n in f["lines"] if n <= len(source.splitlines())],
                        "expected_lines": []
                        if fixed
                        else [n for n in f["lines"] if n <= len(source.splitlines())],
                        "contract": f["contract"],
                        "extra": f["extra"],
                        "purpose": f["purpose"],
                        "document": f["document"],
                        "probes": [
                            {"probe_id": f"p{i + 1}", "call": call}
                            for i, call in enumerate(f["calls"])
                        ],
                        "oracle": [
                            {"probe_id": f"p{i + 1}", **v} for i, v in enumerate(observations)
                        ],
                    }
                )
    return cases


def freeze(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(generate(), ensure_ascii=False, indent=2) + "\n").encode()
    path = root / "corpus.json"
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("FROZEN_CORPUS_CHANGED")
    path.write_bytes(raw)
    manifest = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "cases": 36,
        "development": 20,
        "holdout": 16,
        "provenance": "hand-authored synthetic; no customer code",
        "oracle_review": "agent-authored; trusted reference tests; independent human pending",
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    freeze(Path("evals/quality-lab-20260929"))
