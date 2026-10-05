"""Separate accuracy metrics for review-accuracy-v1 runs. Offline: reads stored run JSON only."""

import argparse
import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

# post(case, result) -> (result_after_post_processing, removed_finding_keys)
PostProcess = Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], set[str]]]


def semantic_grade(case: dict[str, Any], finding: dict[str, Any]) -> str:
    """Heuristic phrase grader. PASS | FAIL_REJECTED | FAIL_NO_EFFECT | FAIL_NO_TRIGGER.

    It never approves semantic quality by itself: manual review stays a separate record.
    """
    spec = case["semantic"]
    text = f"{finding.get('trigger', '')} {finding.get('consequence', '')}"
    if any(phrase in text for phrase in spec["reject_any"]):
        return "FAIL_REJECTED"
    if spec["trigger_any"] and not any(phrase in text for phrase in spec["trigger_any"]):
        return "FAIL_NO_TRIGGER"
    if not any(phrase in text for phrase in spec["effect_any"]):
        return "FAIL_NO_EFFECT"
    return "PASS"


def located(case: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    lo, hi = case["expected_locations"][0]
    return [
        f
        for f in result.get("issues", [])
        if f["file_path"] == case["path"] and lo <= f["line"] <= hi
    ]


def located_relaxed(case: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    """Also accept a finding whose cited evidence lines include the expected line.

    A defect introduced on one line (for example a changed default) is often reported where its
    effect occurs. Strict and relaxed counts are both reported; neither replaces the other.
    """
    lo, hi = case["expected_locations"][0]
    return [
        f
        for f in result.get("issues", [])
        if f["file_path"] == case["path"]
        and (lo <= f["line"] <= hi or any(lo <= n <= hi for n in f.get("evidence_lines", [])))
    ]


def score(
    cases: list[dict[str, Any]],
    records: list[dict[str, Any]],
    post: PostProcess | None = None,
) -> dict[str, Any]:
    by_id = {c["id"]: c for c in cases}
    m: dict[str, Any] = defaultdict(int)
    by_category: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in records:
        case = by_id[item["id"]]
        m["runs"] += 1
        m["input_tokens"] += item.get("input_tokens", 0)
        m["output_tokens"] += item.get("output_tokens", 0)
        if item["status"] != "COMPLETED":
            m["failed_runs"] += 1
            if case["polarity"] == "defect":
                m["defect_runs"] += 1
            else:
                m["clean_runs"] += 1
            continue
        result = item["result"]
        removed: set[str] = set()
        if post is not None:
            result, removed = post(case, result)
        category = by_category[case["category"]]
        if case["polarity"] == "clean":
            m["clean_runs"] += 1
            m["clean_false_positives"] += bool(result.get("issues"))
            m["clean_questions"] += bool(result.get("questions"))
            continue
        m["defect_runs"] += 1
        category["defect_runs"] += 1
        original = located(case, item["result"])
        if located_relaxed(case, item["result"]):
            m["location_found_relaxed"] += 1
        if not original:
            m["location_missed"] += 1
            continue
        m["location_found"] += 1
        category["location_found"] += 1
        before = {f["key"]: semantic_grade(case, f) for f in original}
        for key, grade in before.items():
            if key in removed:
                if grade == "PASS":
                    m["correct_claims_wrongly_dropped"] += 1
                else:
                    m["flawed_claims_dropped"] += 1
        remaining = [f for f in located(case, result)]
        if not remaining:
            m["located_then_removed"] += 1
            continue
        grades = [semantic_grade(case, f) for f in remaining]
        if all(g == "PASS" for g in grades):
            m["semantic_pass"] += 1
            category["semantic_pass"] += 1
        elif any(g == "FAIL_REJECTED" for g in grades):
            m["semantic_fail_rejected"] += 1
        else:
            m["semantic_fail_other"] += 1
    out = dict(m)
    out["style"] = style_metrics(records)
    out["by_category"] = {k: dict(v) for k, v in sorted(by_category.items())}
    return out


# Cue lists were widened AFTER the first junior/senior outputs were read (post-hoc), so the ratio is
# a rough style indicator only; manual review of paired samples is the reference.
STEP_CUES = ("따라가", "그런데", "그래서", "즉 ", "줄에서", "줄은", "→", "예를 들어")
REASON_CUES = (
    "때문",
    "므로",
    "이라서",
    "원인",
    "이유",
    "원리",
    "습관",
    "구분하지 못",
    "막을 수",
    "도움이",
)
PATTERN_CUES = ("하세요", "보세요", "쓰세요", "바꾸", "정하세요", "확인해", "방법이", "쓰면")


def style_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Heuristic voice measures over admitted findings. They describe style, never accuracy."""
    lengths: list[int] = []
    teaching = 0
    for item in records:
        if item.get("status") != "COMPLETED":
            continue
        for f in item["result"].get("issues", []) + item["result"].get("questions", []):
            evidence, suggestion = f.get("evidence", ""), f.get("suggestion", "")
            lengths.append(len(evidence) + len(suggestion))
            steps = any(c in evidence for c in STEP_CUES)
            reason = any(c in evidence + suggestion for c in REASON_CUES)
            pattern = any(c in suggestion for c in PATTERN_CUES)
            teaching += steps and reason and pattern
    lengths.sort()
    median = lengths[len(lengths) // 2] if lengths else 0
    return {
        "findings": len(lengths),
        "median_evidence_plus_suggestion_chars": median,
        "teaching_cue_findings": teaching,
        "teaching_cue_ratio": round(teaching / len(lengths), 3) if lengths else None,
    }


def load(corpus: Path, runs: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases = json.loads(corpus.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for path in runs:
        records += json.loads(path.read_text(encoding="utf-8"))["cases"]
    return cases, records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path)
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    loaded_cases, loaded_records = load(args.corpus, args.runs)
    report = score(loaded_cases, loaded_records)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
