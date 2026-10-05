# ruff: noqa: E501
"""Build the review-accuracy-v1 evaluation corpus. Authored synthetic code; never executed."""

import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path("evals/review-accuracy-v1")

# Each pair: a contract-preserving base, one head that breaks the contract (defect) and one
# behavior-preserving head (clean twin). `inputs` are the oracle probes; `actual`/`expected`
# are value classes. Closed vocabulary: NONE EMPTY_STR ZERO EMPTY_LIST TRUE FALSE INT:<n>
# STR:<s> LIST:<repr> EXC:<Name>. `semantic` lists phrases for the heuristic grader; it never replaces review.

PAIRS = [
    dict(
        pair="or-default-name",
        split="dev",
        category="OR_DEFAULT",
        lang="py",
        path="labels.py",
        contract="An empty string is an intentional name and must be returned unchanged; only None uses the fallback.",
        base='''def label_for(name, fallback):
    """Return the stored name. An empty string is intentional and must be returned
    unchanged; only a missing name (None) uses the fallback."""
    if name is None:
        return fallback
    return name
''',
        defect=(
            '''def label_for(name, fallback):
    """Return the stored name. An empty string is intentional and must be returned
    unchanged; only a missing name (None) uses the fallback."""
    return name or fallback
''',
            "    return name or fallback",
        ),
        clean=(
            '''def label_for(name, fallback):
    """Return the stored name. An empty string is intentional and must be returned
    unchanged; only a missing name (None) uses the fallback."""
    return fallback if name is None else name
''',
            "    return fallback if name is None else name",
        ),
        probes=[
            dict(inputs=dict(name="", fallback="guest"), actual="STR:guest", expected="EMPTY_STR"),
            dict(
                inputs=dict(name=None, fallback="guest"), actual="STR:guest", expected="STR:guest"
            ),
        ],
        semantic=dict(
            trigger_any=["빈 문자열", "''", '""', "empty string"],
            effect_any=["fallback", "대체", "기본값", "덮어", "대신"],
            reject_any=["None을 반환", "None이 반환", "None 반환"],
        ),
    ),
    dict(
        pair="or-default-pagesize",
        split="holdout",
        category="OR_DEFAULT",
        lang="py",
        path="paging.py",
        contract="A requested page size of 0 is valid and must be returned as 0; only None uses the default.",
        base='''def page_size(requested, default_size):
    """Return the requested page size. 0 is a valid request meaning no items;
    only None selects the default."""
    if requested is None:
        return default_size
    return requested
''',
        defect=(
            '''def page_size(requested, default_size):
    """Return the requested page size. 0 is a valid request meaning no items;
    only None selects the default."""
    return requested or default_size
''',
            "    return requested or default_size",
        ),
        clean=(
            '''def page_size(requested, default_size):
    """Return the requested page size. 0 is a valid request meaning no items;
    only None selects the default."""
    return default_size if requested is None else requested
''',
            "    return default_size if requested is None else requested",
        ),
        probes=[
            dict(inputs=dict(requested=0, default_size=25), actual="INT:25", expected="ZERO"),
            dict(inputs=dict(requested=None, default_size=25), actual="INT:25", expected="INT:25"),
        ],
        semantic=dict(
            trigger_any=[
                "requested가 0",
                "requested=0",
                "requested == 0",
                "0이",
                "0일",
                "0을",
                "값 0",
                "0인",
            ],
            effect_any=["기본", "default", "대체", "덮어", "25"],
            reject_any=[],
        ),
    ),
    dict(
        pair="default-arg-notify",
        split="dev",
        category="DEFAULT_ARG",
        lang="py",
        path="notify.py",
        contract="Calling should_notify() with no arguments must notify (True); notifications are enabled by default.",
        base='''def should_notify(enabled=True, urgent=False):
    """Notify when notifications are enabled, or when the event is urgent.
    A call without arguments must notify."""
    return enabled or urgent
''',
        defect=(
            '''def should_notify(enabled=True, urgent=False):
    """Notify when notifications are enabled, or when the event is urgent.
    A call without arguments must notify."""
    return enabled and urgent
''',
            "    return enabled and urgent",
        ),
        clean=(
            '''def should_notify(enabled=True, urgent=False):
    """Notify when notifications are enabled, or when the event is urgent.
    A call without arguments must notify."""
    return urgent or enabled
''',
            "    return urgent or enabled",
        ),
        probes=[
            dict(inputs=dict(), actual="FALSE", expected="TRUE"),
            dict(inputs=dict(enabled=False, urgent=True), actual="FALSE", expected="TRUE"),
        ],
        semantic=dict(
            trigger_any=[
                "인자 없이",
                "기본값",
                "기본 인자",
                "인자 없는",
                "기본 호출",
                "enabled=True",
            ],
            effect_any=["False", "알림", "반환", "거짓"],
            reject_any=["None"],
        ),
    ),
    dict(
        pair="default-arg-retries",
        split="dev",
        category="DEFAULT_ARG",
        lang="py",
        path="retry.py",
        contract="With default arguments retries_left() must be 3.",
        base='''def retries_left(max_retries=3, used=0):
    """Number of retries still available. With default arguments the result is 3."""
    return max_retries - used
''',
        defect=(
            '''def retries_left(max_retries=3, used=1):
    """Number of retries still available. With default arguments the result is 3."""
    return max_retries - used
''',
            "def retries_left(max_retries=3, used=1):",
        ),
        clean=(
            '''def retries_left(max_retries: int = 3, used: int = 0) -> int:
    """Number of retries still available. With default arguments the result is 3."""
    return max_retries - used
''',
            "def retries_left(max_retries: int = 3, used: int = 0) -> int:",
        ),
        probes=[dict(inputs=dict(), actual="INT:2", expected="INT:3")],
        semantic=dict(
            trigger_any=["기본값", "인자 없이", "기본 인자", "used=1", "used의 기본", "기본 호출"],
            effect_any=["2", "3", "남은"],
            reject_any=[],
        ),
    ),
    dict(
        pair="range-step-offsets",
        split="dev",
        category="RANGE_STEP",
        lang="py",
        path="windows.py",
        contract="step is always >= 1; the offsets are 0, step, 2*step ... below total.",
        base='''def window_starts(total, step):
    """Return start offsets 0, step, 2*step ... below total. step is always >= 1."""
    offsets = []
    position = 0
    while position < total:
        offsets.append(position)
        position += step
    return offsets
''',
        defect=(
            '''def window_starts(total, step):
    """Return start offsets 0, step, 2*step ... below total. step is always >= 1."""
    return list(range(0, total, step - 1))
''',
            "    return list(range(0, total, step - 1))",
        ),
        clean=(
            '''def window_starts(total, step):
    """Return start offsets 0, step, 2*step ... below total. step is always >= 1."""
    return list(range(0, total, step))
''',
            "    return list(range(0, total, step))",
        ),
        probes=[
            dict(
                inputs=dict(total=5, step=1),
                actual="EXC:ValueError",
                expected="LIST:[0, 1, 2, 3, 4]",
            ),
            dict(
                inputs=dict(total=5, step=2),
                actual="LIST:[0, 1, 2, 3, 4]",
                expected="LIST:[0, 2, 4]",
            ),
        ],
        semantic=dict(
            trigger_any=["step이 1", "step=1", "step == 1", "step 1", "1일 때", "step이 1일"],
            effect_any=["ValueError", "예외", "step이 0", "step 인자가 0", "0이 되", "step은 0"],
            reject_any=["빈 리스트"],
        ),
    ),
    dict(
        pair="range-step-last",
        split="holdout",
        category="RANGE_STEP",
        lang="py",
        path="recent.py",
        contract="last_indexes(count, size) returns the indexes of the last count items, newest first. count >= 1.",
        base='''def last_indexes(count, size):
    """Indexes of the last `count` items of a list of length `size`, newest first.
    count is at least 1 and never larger than size."""
    result = []
    index = size - 1
    while len(result) < count:
        result.append(index)
        index -= 1
    return result
''',
        defect=(
            '''def last_indexes(count, size):
    """Indexes of the last `count` items of a list of length `size`, newest first.
    count is at least 1 and never larger than size."""
    return list(range(size - 1, size - count, 1))
''',
            "    return list(range(size - 1, size - count, 1))",
        ),
        clean=(
            '''def last_indexes(count, size):
    """Indexes of the last `count` items of a list of length `size`, newest first.
    count is at least 1 and never larger than size."""
    return list(range(size - 1, size - 1 - count, -1))
''',
            "    return list(range(size - 1, size - 1 - count, -1))",
        ),
        probes=[
            dict(inputs=dict(count=2, size=5), actual="EMPTY_LIST", expected="LIST:[4, 3]"),
            dict(inputs=dict(count=1, size=5), actual="EMPTY_LIST", expected="LIST:[4]"),
        ],
        semantic=dict(
            trigger_any=[],
            effect_any=["빈 리스트", "빈 결과", "비어", "아무 인덱스도", "빈 목록"],
            reject_any=["ValueError", "예외가 발생"],
        ),
    ),
    dict(
        pair="dict-get-timeout",
        split="dev",
        category="DICT_GET",
        lang="py",
        path="settings.py",
        contract="A configured timeout of 0 means no timeout and must be returned as 0; only a missing key uses 30.",
        base='''def read_timeout(config):
    """Timeout in seconds. A configured 0 means no timeout and is returned as 0;
    only a missing key falls back to 30."""
    if "timeout" in config:
        return config["timeout"]
    return 30
''',
        defect=(
            '''def read_timeout(config):
    """Timeout in seconds. A configured 0 means no timeout and is returned as 0;
    only a missing key falls back to 30."""
    return config.get("timeout") or 30
''',
            '    return config.get("timeout") or 30',
        ),
        clean=(
            '''def read_timeout(config):
    """Timeout in seconds. A configured 0 means no timeout and is returned as 0;
    only a missing key falls back to 30."""
    return config.get("timeout", 30)
''',
            '    return config.get("timeout", 30)',
        ),
        probes=[
            dict(inputs=dict(config={"timeout": 0}), actual="INT:30", expected="ZERO"),
            dict(inputs=dict(config={}), actual="INT:30", expected="INT:30"),
        ],
        semantic=dict(
            trigger_any=[
                "timeout이 0",
                "0으로",
                "0이 설정",
                "값이 0",
                "timeout: 0",
                "0인 경우",
                "0일 때",
                "0이면",
                "0 값",
            ],
            effect_any=["30"],
            reject_any=[],
        ),
    ),
    dict(
        pair="dict-get-flag",
        split="holdout",
        category="DICT_GET",
        lang="py",
        path="flags.py",
        contract="A flag that is missing from flags is disabled (False).",
        base='''def is_enabled(flags, name):
    """True only when the flag exists and is exactly True. A missing flag is disabled."""
    return name in flags and flags[name] is True
''',
        defect=(
            '''def is_enabled(flags, name):
    """True only when the flag exists and is exactly True. A missing flag is disabled."""
    return flags.get(name, True)
''',
            "    return flags.get(name, True)",
        ),
        clean=(
            '''def is_enabled(flags, name):
    """True only when the flag exists and is exactly True. A missing flag is disabled."""
    return flags.get(name, False) is True
''',
            "    return flags.get(name, False) is True",
        ),
        probes=[dict(inputs=dict(flags={}, name="beta"), actual="TRUE", expected="FALSE")],
        semantic=dict(
            trigger_any=["없는", "누락", "존재하지 않", "키가 없", "플래그가 없", "정의되지 않"],
            effect_any=["True", "활성", "켜"],
            reject_any=["KeyError", "예외"],
        ),
    ),
    dict(
        pair="none-vs-falsy-items",
        split="dev",
        category="NONE_VS_FALSY",
        lang="py",
        path="inputs.py",
        contract="has_value returns True for any list, including an empty list; only None means not provided.",
        base='''def has_value(items):
    """True when items was provided, even if it is an empty list.
    Only None means not provided."""
    return items is not None
''',
        defect=(
            '''def has_value(items):
    """True when items was provided, even if it is an empty list.
    Only None means not provided."""
    return bool(items)
''',
            "    return bool(items)",
        ),
        clean=(
            '''def has_value(items):
    """True when items was provided, even if it is an empty list.
    Only None means not provided."""
    return not (items is None)
''',
            "    return not (items is None)",
        ),
        probes=[
            dict(inputs=dict(items=[]), actual="FALSE", expected="TRUE"),
            dict(inputs=dict(items=None), actual="FALSE", expected="FALSE"),
        ],
        semantic=dict(
            trigger_any=["빈 리스트", "[]", "빈 목록", "비어 있는", "빈 배열"],
            effect_any=["False", "거짓", "제공되지 않은", "없는 것으로"],
            reject_any=["None이면 True", "None일 때 True"],
        ),
    ),
    dict(
        pair="none-vs-falsy-text",
        split="dev",
        category="NONE_VS_FALSY",
        lang="py",
        path="text.py",
        contract="normalize keeps an empty string as an empty string; only None maps to None.",
        base='''def normalize(text):
    """Strip surrounding whitespace. None stays None and an empty string stays
    an empty string."""
    if text is None:
        return None
    return text.strip()
''',
        defect=(
            '''def normalize(text):
    """Strip surrounding whitespace. None stays None and an empty string stays
    an empty string."""
    if not text:
        return None
    return text.strip()
''',
            "    if not text:",
        ),
        clean=(
            '''def normalize(text):
    """Strip surrounding whitespace. None stays None and an empty string stays
    an empty string."""
    return None if text is None else text.strip()
''',
            "    return None if text is None else text.strip()",
        ),
        probes=[dict(inputs=dict(text=""), actual="NONE", expected="EMPTY_STR")],
        semantic=dict(
            trigger_any=["빈 문자열", "''", '""', "empty string"],
            effect_any=["None"],
            reject_any=[],
        ),
    ),
    dict(
        pair="length-fits",
        split="dev",
        category="LENGTH_BOUNDARY",
        lang="py",
        path="names.py",
        contract="A name with exactly 8 characters fits.",
        base='''def fits(name):
    """A name fits when it has at most 8 characters; exactly 8 is allowed."""
    return len(name) <= 8
''',
        defect=(
            '''def fits(name):
    """A name fits when it has at most 8 characters; exactly 8 is allowed."""
    return len(name) < 8
''',
            "    return len(name) < 8",
        ),
        clean=(
            '''def fits(name):
    """A name fits when it has at most 8 characters; exactly 8 is allowed."""
    return not len(name) > 8
''',
            "    return not len(name) > 8",
        ),
        probes=[dict(inputs=dict(name="abcdefgh"), actual="FALSE", expected="TRUE")],
        semantic=dict(
            trigger_any=[
                "8자",
                "8글자",
                "길이가 8",
                "정확히 8",
                "== 8",
                "8 문자",
                "8개 문자",
                "8인",
            ],
            effect_any=["False", "거부", "허용되지", "실패", "거짓", "맞지 않"],
            reject_any=[],
        ),
    ),
    dict(
        pair="length-last",
        split="holdout",
        category="LENGTH_BOUNDARY",
        lang="py",
        path="seq.py",
        contract="last_item returns the final element of a non-empty list.",
        base='''def last_item(items):
    """Return the last element, or None for an empty list."""
    if len(items) == 0:
        return None
    return items[len(items) - 1]
''',
        defect=(
            '''def last_item(items):
    """Return the last element, or None for an empty list."""
    if len(items) == 0:
        return None
    return items[len(items)]
''',
            "    return items[len(items)]",
        ),
        clean=(
            '''def last_item(items):
    """Return the last element, or None for an empty list."""
    if len(items) == 0:
        return None
    return items[-1]
''',
            "    return items[-1]",
        ),
        probes=[dict(inputs=dict(items=[1, 2, 3]), actual="EXC:IndexError", expected="INT:3")],
        semantic=dict(
            trigger_any=[
                "비어 있지 않은",
                "항목이 있는",
                "원소가 있는",
                "len(items)",
                "리스트에",
                "요소가",
            ],
            effect_any=["IndexError", "범위", "예외", "인덱스"],
            reject_any=[],
        ),
    ),
    dict(
        pair="java-null-empty",
        split="dev",
        category="NONE_VS_FALSY",
        lang="java",
        path="Names.java",
        contract="An empty string is returned unchanged; only null uses the fallback.",
        base="""class Names {
    /** Display name. An empty string is intentional and returned unchanged;
     * only null uses the fallback. */
    static String display(String name, String fallback) {
        if (name == null) {
            return fallback;
        }
        return name;
    }
}
""",
        defect=(
            """class Names {
    /** Display name. An empty string is intentional and returned unchanged;
     * only null uses the fallback. */
    static String display(String name, String fallback) {
        if (name == null || name.isEmpty()) {
            return fallback;
        }
        return name;
    }
}
""",
            "        if (name == null || name.isEmpty()) {",
        ),
        clean=(
            """class Names {
    /** Display name. An empty string is intentional and returned unchanged;
     * only null uses the fallback. */
    static String display(String name, String fallback) {
        return name == null ? fallback : name;
    }
}
""",
            "        return name == null ? fallback : name;",
        ),
        probes=[
            dict(inputs=dict(name="", fallback="guest"), actual="STR:guest", expected="EMPTY_STR")
        ],
        semantic=dict(
            trigger_any=["빈 문자열", '""', "isEmpty", "빈 이름", "empty string"],
            effect_any=["fallback", "대체", "기본", "덮어", "대신"],
            reject_any=[],
        ),
    ),
    dict(
        pair="java-length-tag",
        split="holdout",
        category="LENGTH_BOUNDARY",
        lang="java",
        path="Limits.java",
        contract="A tag with exactly 16 characters is valid.",
        base="""class Limits {
    /** A tag is valid when it has at most 16 characters; exactly 16 is allowed. */
    static boolean valid(String tag) {
        return tag.length() <= 16;
    }
}
""",
        defect=(
            """class Limits {
    /** A tag is valid when it has at most 16 characters; exactly 16 is allowed. */
    static boolean valid(String tag) {
        return tag.length() < 16;
    }
}
""",
            "        return tag.length() < 16;",
        ),
        clean=(
            """class Limits {
    /** A tag is valid when it has at most 16 characters; exactly 16 is allowed. */
    static boolean valid(String tag) {
        return !(tag.length() > 16);
    }
}
""",
            "        return !(tag.length() > 16);",
        ),
        probes=[dict(inputs=dict(tag="a" * 16), actual="FALSE", expected="TRUE")],
        semantic=dict(
            trigger_any=["16자", "16글자", "길이가 16", "정확히 16", "== 16", "16 문자", "16개"],
            effect_any=["false", "False", "거부", "허용되지", "실패", "거짓", "유효하지"],
            reject_any=[],
        ),
    ),
    dict(
        pair="java-pages",
        split="dev",
        category="ARITH_BOUNDARY",
        lang="java",
        path="Pages.java",
        contract="pages(count, pageSize) rounds up: 11 items with page size 10 need 2 pages.",
        base="""class Pages {
    /** Pages needed for count items at pageSize items per page, rounded up.
     * count >= 0 and pageSize >= 1. */
    static int pages(int count, int pageSize) {
        return (count + pageSize - 1) / pageSize;
    }
}
""",
        defect=(
            """class Pages {
    /** Pages needed for count items at pageSize items per page, rounded up.
     * count >= 0 and pageSize >= 1. */
    static int pages(int count, int pageSize) {
        return count / pageSize;
    }
}
""",
            "        return count / pageSize;",
        ),
        clean=(
            """class Pages {
    /** Pages needed for count items at pageSize items per page, rounded up.
     * count >= 0 and pageSize >= 1. */
    static int pages(int count, int pageSize) {
        return Math.floorDiv(count + pageSize - 1, pageSize);
    }
}
""",
            "        return Math.floorDiv(count + pageSize - 1, pageSize);",
        ),
        probes=[dict(inputs=dict(count=11, pageSize=10), actual="INT:1", expected="INT:2")],
        semantic=dict(
            trigger_any=["나누어 떨어지지", "나머지", "올림", "11", "남는", "딱 나누어"],
            effect_any=["내림", "잘려", "1", "부족", "적게", "버려"],
            reject_any=[],
        ),
    ),
    dict(
        pair="java-access",
        split="holdout",
        category="BOOL_PRECEDENCE",
        lang="java",
        path="Access.java",
        contract="allowed requires active AND (admin OR owner); an inactive user is never allowed.",
        base="""class Access {
    /** Allowed when the user is active AND (admin OR owner). */
    static boolean allowed(boolean active, boolean admin, boolean owner) {
        return active && (admin || owner);
    }
}
""",
        defect=(
            """class Access {
    /** Allowed when the user is active AND (admin OR owner). */
    static boolean allowed(boolean active, boolean admin, boolean owner) {
        return active && admin || owner;
    }
}
""",
            "        return active && admin || owner;",
        ),
        clean=(
            """class Access {
    /** Allowed when the user is active AND (admin OR owner). */
    static boolean allowed(boolean active, boolean admin, boolean owner) {
        return active && (owner || admin);
    }
}
""",
            "        return active && (owner || admin);",
        ),
        probes=[
            dict(
                inputs=dict(active=False, admin=False, owner=True), actual="TRUE", expected="FALSE"
            )
        ],
        semantic=dict(
            trigger_any=[
                "active가 false",
                "비활성",
                "active=false",
                "active == false",
                "active가 아닌",
                "!active",
            ],
            effect_any=["owner", "true", "허용", "통과", "True"],
            reject_any=[],
        ),
    ),
]


def make_patch(old: str, new: str) -> str:
    lines = list(
        difflib.unified_diff(old.splitlines(), new.splitlines(), "a", "b", n=200, lineterm="")
    )
    return "\n".join(lines[2:])


def head_line(source: str, snippet: str) -> int:
    rows = source.splitlines()
    matches = [i for i, row in enumerate(rows, 1) if row == snippet]
    if len(matches) != 1:
        raise ValueError(f"changed line must be unique: {snippet!r}")
    return matches[0]


def build_cases() -> list[dict]:
    cases = []
    for pair in PAIRS:
        for polarity in ("defect", "clean"):
            head, snippet = pair[polarity]
            line = head_line(head, snippet)
            if pair["lang"] == "py":
                ast.parse(head)  # parse only: authored code is never executed or imported
            probes = pair["probes"]
            if polarity == "clean":
                probes = [{**p, "actual": p["expected"]} for p in probes]
            case = {
                "id": f"{pair['pair']}-{polarity}",
                "path": pair["path"],
                "patch": make_patch(pair["base"], head),
                "expected_locations": [[line, line]] if polarity == "defect" else [],
                "expected_lines": [],
                "contract": pair["contract"],
                "kind": "synthetic-value-semantics",
                "split": pair["split"],
                "category": pair["category"],
                "polarity": polarity,
                "pair_id": pair["pair"],
                "language": pair["lang"],
                "oracle": {"line": line, "probes": probes},
                "label_review": "agent-oracle; independent-human-review-pending",
                "rubric": {
                    "required_behavior": pair["contract"],
                    "reject": "wrong value or exception stated for the trigger, invented contract, "
                    "unreachable trigger, duplicate or generic question",
                },
                "provenance": {
                    "transformation": "handwritten synthetic reproduction; not derived from a real PR",
                    "authored": "2026-10-05",
                },
            }
            if polarity == "defect":
                case["semantic"] = pair["semantic"]
            cases.append(case)
    return cases


def sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def write(root: Path = ROOT) -> dict:
    cases = build_cases()
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("UNIQUE_IDS_REQUIRED")
    root.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "scope": "Labels, oracle and semantic phrases are never sent to the model.",
        "independent_human_review": False,
        "frozen_at": "2026-10-05",
        "corpora": {},
    }
    for split in ("dev", "holdout"):
        subset = [c for c in cases if c["split"] == split]
        (root / f"cases-{split}.json").write_text(
            json.dumps(subset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest["corpora"][split] = {
            "sha256": hashlib.sha256((root / f"cases-{split}.json").read_bytes()).hexdigest(),
            "cases": len(subset),
            "defects": sum(c["polarity"] == "defect" for c in subset),
            "case_ids": [c["id"] for c in subset],
        }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(
        json.dumps(
            {
                k: {x: y for x, y in v.items() if x != "case_ids"}
                for k, v in write()["corpora"].items()
            }
        )
    )
