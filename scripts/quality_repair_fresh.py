"""Twelve new authored fixtures; sources are data and never imported/executed."""

from scripts.quality_lab_protocol import digest


def cases():
    pairs = [
        (
            "await-save",
            "save.js",
            "Must finish persistence before returning true. save returns a Promise.",
            "async function submit(store, value) {\n  store.save(value);\n  return true;\n}",
            "async function submit(store, value) {\n  await store.save(value);\n  return true;\n}",
            [2, 3],
        ),
        (
            "tenant-sql",
            "load.py",
            "order_id may repeat across tenants. Return only the authenticated tenant's order.",
            "def load(db, order_id, tenant_id):\n"
            "    return db.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()",
            "def load(db, order_id, tenant_id):\n"
            "    return db.execute('SELECT * FROM orders WHERE id = ? AND tenant_id = ?', "
            "(order_id, tenant_id)).fetchone()",
            [2],
        ),
        (
            "array-index",
            "Last.java",
            "Return the last element of nonempty int arrays. Caller rejects empty arrays.",
            "class Last {\n  int last(int[] values) {\n    return values[values.length];\n  }\n}",
            "class Last {\n  int last(int[] values) {\n"
            "    return values[values.length - 1];\n  }\n}",
            [3],
        ),
        (
            "close-error",
            "read.py",
            "Always close streams including when read raises. "
            "opener returns a standard context-managed file stream.",
            "def read(opener):\n    stream = opener()\n    value = stream.read()\n"
            "    stream.close()\n    return value",
            "def read(opener):\n    with opener() as stream:\n        return stream.read()",
            [2, 3, 4],
        ),
        (
            "sort-state",
            "sort.js",
            "Return finite numbers in ascending order. Do not modify the caller's array.",
            "function ordered(values) {\n  return values.sort((a, b) => a - b);\n}",
            "function ordered(values) {\n  return [...values].sort((a, b) => a - b);\n}",
            [2],
        ),
        (
            "auth-fail-open",
            "access.py",
            "checker raises TimeoutError when authorization is unknown. "
            "Unknown authorization must deny access.",
            "def allowed(checker, user):\n    try:\n        return checker(user)\n"
            "    except TimeoutError:\n        return True",
            "def allowed(checker, user):\n    try:\n        return checker(user)\n"
            "    except TimeoutError:\n        return False",
            [4, 5],
        ),
    ]
    result = []
    for family, path, contract, bad, good, locations in pairs:
        for fixed, text in [(False, bad), (True, good)]:
            lines = text.splitlines()
            result.append(
                {
                    "id": digest("fresh:" + family + str(fixed))[:12],
                    "family": family,
                    "fixed": fixed,
                    "path": path,
                    "contract": contract,
                    "patch": f"@@ -0,0 +1,{len(lines)} @@\n" + "\n".join("+" + x for x in lines),
                    "expected_lines": [] if fixed else locations,
                    "oracle": [],
                }
            )
    return result
