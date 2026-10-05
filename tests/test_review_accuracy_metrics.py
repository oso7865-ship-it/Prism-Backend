import json
from pathlib import Path

from scripts.review_accuracy_evaluation import located, located_relaxed, score, semantic_grade

CASES = json.loads(Path("evals/review-accuracy-v1/cases-dev.json").read_text(encoding="utf-8"))
BY_ID = {c["id"]: c for c in CASES}
DEFECT = BY_ID["or-default-name-defect"]
CLEAN = BY_ID["or-default-name-clean"]


def finding(case, trigger, consequence, key="k1", line=None):
    return {
        "key": key,
        "file_path": case["path"],
        "line": line or case["expected_locations"][0][0],
        "trigger": trigger,
        "consequence": consequence,
    }


def record(case, issues=(), status="COMPLETED", tokens=(10, 5)):
    item = {"id": case["id"], "repeat": 1, "status": status}
    item["input_tokens"], item["output_tokens"] = tokens
    if status == "COMPLETED":
        item["result"] = {"issues": list(issues), "questions": []}
    return item


GOOD = finding(DEFECT, "name이 빈 문자열일 때", "빈 문자열이 fallback으로 대체됩니다.")
WRONG = finding(DEFECT, "name이 빈 문자열일 때", "None을 반환합니다.")
VAGUE = finding(DEFECT, "name 값이 비어 있을 때", "다른 값이 사용됩니다.")


def test_semantic_grader_separates_correct_wrong_and_vague():
    assert semantic_grade(DEFECT, GOOD) == "PASS"
    assert semantic_grade(DEFECT, WRONG) == "FAIL_REJECTED"
    assert semantic_grade(DEFECT, VAGUE) == "FAIL_NO_TRIGGER"


def test_locating_uses_expected_line_and_path_only():
    other = finding(DEFECT, "x", "y", line=DEFECT["expected_locations"][0][0] + 1)
    assert located(DEFECT, {"issues": [GOOD, other]}) == [GOOD]


def test_metrics_are_reported_separately_never_as_one_score():
    records = [
        record(DEFECT, [GOOD]),
        record(DEFECT, [WRONG], tokens=(20, 8)),
        record(DEFECT, []),
        record(CLEAN, [finding(CLEAN, "a", "b", key="c1", line=4)]),
        record(CLEAN, []),
        record(DEFECT, status="FAILED"),
    ]
    out = score(CASES, records)
    assert out["runs"] == 6
    assert out["defect_runs"] == 4
    assert out["clean_runs"] == 2
    assert out["location_found"] == 2
    assert out["location_missed"] == 1
    assert out["semantic_pass"] == 1
    assert out["semantic_fail_rejected"] == 1
    assert out["clean_false_positives"] == 1
    assert out["failed_runs"] == 1
    assert out["input_tokens"] == 10 + 20 + 10 + 10 + 10 + 10
    assert "or-default-name" not in json.dumps(out)  # no case text or labels leak into metrics


def test_post_processing_effects_are_attributed_correctly():
    def drop_all(case, result):
        keys = {f["key"] for f in result["issues"]}
        return {**result, "issues": []}, keys

    correct = score(CASES, [record(DEFECT, [GOOD])], post=drop_all)
    assert correct["correct_claims_wrongly_dropped"] == 1
    assert correct["located_then_removed"] == 1
    assert "semantic_pass" not in correct

    flawed = score(CASES, [record(DEFECT, [WRONG])], post=drop_all)
    assert flawed["flawed_claims_dropped"] == 1
    assert "correct_claims_wrongly_dropped" not in flawed


def test_relaxed_location_accepts_cited_evidence_but_strict_does_not():
    elsewhere = finding(DEFECT, "x", "y", line=DEFECT["expected_locations"][0][0] + 1)
    elsewhere["evidence_lines"] = [DEFECT["expected_locations"][0][0]]
    result = {"issues": [elsewhere]}
    assert located(DEFECT, result) == []
    assert located_relaxed(DEFECT, result) == [elsewhere]
    out = score(CASES, [record(DEFECT, [elsewhere])])
    assert out["location_missed"] == 1
    assert out["location_found_relaxed"] == 1


def test_style_metrics_measure_voice_without_claiming_accuracy():
    from scripts.review_accuracy_evaluation import style_metrics

    teaching = {
        "evidence": (
            "average([])를 따라가 볼게요. 3줄에서 0으로 나눠요. 나누기 전에 확인하는 습관이 좋아요."
        ),
        "suggestion": (
            "빈 리스트일 때 결과를 먼저 정하세요. 길이를 확인하면 같은 실수를 막을 수 있어요."
        ),
    }
    terse = {"evidence": "3줄이 0으로 나눕니다.", "suggestion": "0개 처리를 추가하세요."}
    records = [
        {"status": "COMPLETED", "result": {"issues": [teaching], "questions": []}},
        {"status": "COMPLETED", "result": {"issues": [terse], "questions": []}},
        {"status": "FAILED"},
    ]
    out = style_metrics(records)
    assert out["findings"] == 2
    assert out["teaching_cue_findings"] == 1 and out["teaching_cue_ratio"] == 0.5
    assert style_metrics([])["teaching_cue_ratio"] is None
