# ruff: noqa: E501
"""Build the synthetic beginner-mistake corpus used to judge junior-mode helpfulness.

All sources are handwritten here; none is derived from a real repository or PR.
Each case is a full before/after file; the patch is generated with difflib.
"""

import difflib
import json
from pathlib import Path

OUT = (
    Path(__file__).resolve().parent.parent
    / "evals"
    / "review-modes-v1"
    / "cases-junior-friendly.json"
)

# (id, path, polarity, before, after)
CASES = [
    (
        "py-mutable-default-defect",
        "tags.py",
        "defect",
        "# Collects tags for one post.\ndef add_tag(tag, tags=None):\n    tags = tags or []\n    tags.append(tag)\n    return tags\n",
        "# Collects tags for one post.\ndef add_tag(tag, tags=[]):\n    tags.append(tag)\n    return tags\n",
    ),
    (
        "py-mutable-default-clean",
        "tags.py",
        "clean",
        "# Collects tags for one post.\ndef add_tag(tag, tags=[]):\n    tags.append(tag)\n    return tags\n",
        "# Collects tags for one post.\ndef add_tag(tag, tags=None):\n    if tags is None:\n        tags = []\n    tags.append(tag)\n    return tags\n",
    ),
    (
        "py-off-by-one-defect",
        "report.py",
        "defect",
        "def print_rows(rows):\n    for i in range(len(rows)):\n        print(i, rows[i])\n",
        "def print_rows(rows):\n    for i in range(len(rows) + 1):\n        print(i, rows[i])\n",
    ),
    (
        "py-string-is-defect",
        "state.py",
        "defect",
        "def is_finished(status):\n    if status == 'done':\n        return True\n    return False\n",
        "def is_finished(status):\n    if status is 'done':\n        return True\n    return False\n",
    ),
    (
        "py-average-empty-defect",
        "stats.py",
        "defect",
        'def average(scores):\n    """Average of the scores. The list is empty when nobody has played yet."""\n    return sum(scores) / max(len(scores), 1)\n',
        'def average(scores):\n    """Average of the scores. The list is empty when nobody has played yet."""\n    return sum(scores) / len(scores)\n',
    ),
    (
        "py-average-empty-clean",
        "stats.py",
        "clean",
        'def average(scores):\n    """Average of the scores. The list is empty when nobody has played yet."""\n    return sum(scores) / len(scores)\n',
        'def average(scores):\n    """Average of the scores. The list is empty when nobody has played yet."""\n    if not scores:\n        return 0.0\n    return sum(scores) / len(scores)\n',
    ),
    (
        "js-foreach-async-defect",
        "save.js",
        "defect",
        "async function saveAll(items) {\n  for (const item of items) {\n    await save(item);\n  }\n  console.log('all saved');\n}\n",
        "async function saveAll(items) {\n  items.forEach(async (item) => {\n    await save(item);\n  });\n  console.log('all saved');\n}\n",
    ),
    (
        "js-foreach-async-clean",
        "save.js",
        "clean",
        "async function saveAll(items) {\n  items.forEach(async (item) => {\n    await save(item);\n  });\n  console.log('all saved');\n}\n",
        "async function saveAll(items) {\n  for (const item of items) {\n    await save(item);\n  }\n  console.log('all saved');\n}\n",
    ),
    (
        "js-var-closure-defect",
        "timers.js",
        "defect",
        "// Print 0, 1, 2 one second apart.\nfor (let i = 0; i < 3; i++) {\n  setTimeout(() => console.log(i), i * 1000);\n}\n",
        "// Print 0, 1, 2 one second apart.\nfor (var i = 0; i < 3; i++) {\n  setTimeout(() => console.log(i), i * 1000);\n}\n",
    ),
    (
        "ts-reduce-empty-defect",
        "cart.ts",
        "defect",
        "// An empty cart is valid and must total 0.\nexport function total(prices: number[]): number {\n  return prices.reduce((sum, price) => sum + price, 0);\n}\n",
        "// An empty cart is valid and must total 0.\nexport function total(prices: number[]): number {\n  return prices.reduce((sum, price) => sum + price);\n}\n",
    ),
    (
        "java-string-equals-defect",
        "Login.java",
        "defect",
        'class Login {\n    boolean isAdmin(User user) {\n        if ("admin".equals(user.getRole())) {\n            return true;\n        }\n        return false;\n    }\n}\n',
        'class Login {\n    boolean isAdmin(User user) {\n        if (user.getRole() == "admin") {\n            return true;\n        }\n        return false;\n    }\n}\n',
    ),
    (
        "java-string-equals-clean",
        "Login.java",
        "clean",
        'class Login {\n    boolean isAdmin(User user) {\n        if (user.getRole() == "admin") {\n            return true;\n        }\n        return false;\n    }\n}\n',
        'class Login {\n    boolean isAdmin(User user) {\n        if ("admin".equals(user.getRole())) {\n            return true;\n        }\n        return false;\n    }\n}\n',
    ),
    (
        "java-int-division-defect",
        "Score.java",
        "defect",
        "class Score {\n    // Returns the average, for example 7 points over 2 games is 3.5.\n    double average(int total, int count) {\n        return (double) total / count;\n    }\n}\n",
        "class Score {\n    // Returns the average, for example 7 points over 2 games is 3.5.\n    double average(int total, int count) {\n        return total / count;\n    }\n}\n",
    ),
    (
        "java-int-division-clean",
        "Score.java",
        "clean",
        "class Score {\n    // Returns the average, for example 7 points over 2 games is 3.5.\n    double average(int total, int count) {\n        return total / count;\n    }\n}\n",
        "class Score {\n    // Returns the average, for example 7 points over 2 games is 3.5.\n    double average(int total, int count) {\n        return (double) total / count;\n    }\n}\n",
    ),
]

LANGUAGE = {"py": "py", "js": "js", "ts": "ts", "java": "java"}


def make_patch(before: str, after: str) -> str:
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=3))
    return "\n".join(diff[2:])  # drop the ---/+++ file headers; keep the @@ hunks


def main() -> None:
    cases = [
        {
            "id": case_id,
            "path": path,
            "patch": make_patch(before, after),
            "language": LANGUAGE[case_id.split("-")[0]],
            "polarity": polarity,
        }
        for case_id, path, polarity, before, after in CASES
    ]
    OUT.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(cases), "cases,", sum(c["polarity"] == "defect" for c in cases), "defects")


if __name__ == "__main__":
    main()
