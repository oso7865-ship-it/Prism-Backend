"""Deterministic measurements from saved, validated synthetic experiment outputs."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from scripts.quality_lab_runner import CAMPAIGN, MAXIMUM, MINIMUM, START
from scripts.stabilize_review_quality import save


def percentile(values, q):
    return sorted(values)[max(0, math.ceil(len(values) * q) - 1)] if values else 0


def report(root):
    folder = root / CAMPAIGN
    rows = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((folder / "results").glob("*.json"))
    ]
    # Do not compare 48 mixed control cases against 36 new candidate cases.
    for row in rows:
        if row["split"] == "bridge":
            row["split"] = (
                "bridge_regression" if row.get("legacy_seen_before") else "bridge_synthetic"
            )
    calls = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted((folder / "calls").glob("*.json"))
    ]
    usage = json.loads((root / "usage.json").read_text(encoding="utf-8"))
    actual = sum(a["run"] == CAMPAIGN for a in usage["attempts"])
    table = []
    for split, arm in sorted({(r["split"], r["arm"]) for r in rows}):
        group = [r for r in rows if (r["split"], r["arm"]) == (split, arm)]
        metrics = [r["metrics"] for r in group]
        table.append(
            {
                "split": split,
                "arm": arm,
                "case_runs": len(group),
                "distinct_cases": len({r["case"] for r in group}),
                "bug_runs": sum(m["expected_bug"] for m in metrics),
                "misses": sum(m["miss"] for m in metrics),
                "normal_false_positives": sum(m["normal_false_positive"] for m in metrics),
                "questions": sum(m["questions"] for m in metrics),
                "invalid_final": sum(not m["valid"] for m in metrics),
                "incomplete_pipeline": sum(not r["pipeline_complete"] for r in group),
                "probe_correct": sum(m["probe_correct"] for m in metrics),
                "probe_total": sum(m["probe_total"] for m in metrics),
                "calls": sum(r["stages"] for r in group),
                "input_tokens": sum(r["input_tokens"] for r in group),
                "output_tokens": sum(r["output_tokens"] for r in group),
                "p50_seconds": round(percentile([r["elapsed_seconds"] for r in group], 0.5), 2),
                "p95_seconds": round(percentile([r["elapsed_seconds"] for r in group], 0.95), 2),
                "verifier_induced_misses": sum(
                    r.get("verifier_induced_miss", False) for r in group
                ),
            }
        )
    failures = []
    for row in rows:
        m = row["metrics"]
        if (
            m["miss"]
            or m["normal_false_positive"]
            or not m["valid"]
            or m["probe_correct"] < m["probe_total"]
            or m["questions"]
        ):
            failures.append(
                {
                    "key": row["key"],
                    "metrics": m,
                    "output": row["output"],
                    "verifier_induced_miss": row.get("verifier_induced_miss", False),
                }
            )
    measured = {
        "campaign": CAMPAIGN,
        "minimum": MINIMUM,
        "maximum": MAXIMUM,
        "campaign_attempts": actual,
        "all_time_attempts": len(usage["attempts"]),
        "prior_attempts": START,
        "call_files": len(calls),
        "call_status": dict(Counter(c["status"] for c in calls)),
        "minimum_met": actual >= MINIMUM,
        "within_maximum": actual <= MAXIMUM,
        "input_tokens": sum(c.get("input_tokens", 0) for c in calls),
        "output_tokens": sum(c.get("output_tokens", 0) for c in calls),
        "tables": table,
        "caveats": [
            "Repeated cases are not independent samples.",
            "Location detection is not verified natural-language explanation accuracy.",
            "Diagnostic probes and tiny functions make this easier than real PRs.",
            "E01 reduced-context UNKNOWN responses are not automatically hallucinations.",
            "Token totals exclude unavailable provider usage on failed calls.",
            "Time is sum of per-stage API/validation latency, not queue/user UI latency.",
        ],
    }
    save(folder / "measurements.json", measured)
    save(folder / "failure-audit-input.json", failures)
    lines = [
        "# 품질 실험 측정값",
        "",
        f"이번 캠페인 {actual}회 / 최소 {MINIMUM}회 / 최대 {MAXIMUM}회.",
        "",
        "| 구분 | 실험 | 평가 | 결함 누락 | 정상 오탐 | 질문 | 형식 실패 "
        "| 값 정확 | 호출 | 중앙/상위95%초 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for t in table:
        lines.append(
            f"| {t['split']} | {t['arm']} | {t['case_runs']} | {t['misses']}/{t['bug_runs']} "
            f"| {t['normal_false_positives']} | {t['questions']} | {t['invalid_final']} "
            f"| {t['probe_correct']}/{t['probe_total']} | {t['calls']} "
            f"| {t['p50_seconds']}/{t['p95_seconds']} |"
        )
    lines += [
        "",
        "반복 평가를 독립 사례로 세지 않는다. 위치 적중은 설명의 의미 정확도를 보증하지 않는다.",
        "작은 합성 코드·관측 입력을 제공한 실험이며 실제 PR 전체 성능으로 일반화할 수 없다.",
        "E01 정보 축소 조건의 UNKNOWN은 근거 부족을 올바르게 표현한 것일 수 있다.",
        "시간은 단계별 API/검증 시간의 합이며 UI 대기 시간은 아니다. "
        "비용은 공급자 과금표를 적용하지 않은 토큰 수로 기록한다.",
        "",
    ]
    (folder / "measurements.md").write_text("\n".join(lines), encoding="utf-8")
    return {k: v for k, v in measured.items() if k not in ("tables", "caveats")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.root)))
