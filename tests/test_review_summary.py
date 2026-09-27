import json

import pytest

from app.domain.review.policy import prepare, validate_result


def item(title="검토 항목", severity="WARNING", question=False):
    return {
        "file_id": "f1",
        "line": 1,
        "evidence_lines": [1],
        "severity": severity,
        "basis": "NEEDS_CONTEXT" if question else "SUPPORTED",
        "trigger": "발생 조건",
        "consequence": "발생 결과",
        "assumptions": ["외부 입력 도달 가능성"] if question else [],
        "title": title,
        "evidence": "근거",
        "suggestion": "제안",
    }


def review(items, summary="모든 경로가 안전합니다."):
    bundle = prepare([{"filename": "a.py", "patch": "@@ -0,0 +1 @@\n+x = 1"}], [], [])
    return validate_result(
        json.dumps({"summary": summary, "issues": items, "limitations": "미제공 문맥"}), bundle
    )


def test_contradictory_model_overview_is_not_displayed_or_persisted():
    result = review([item("null 입력에서 예외가 발생합니다")])
    assert "모든 경로가 안전" not in json.dumps(result, ensure_ascii=False)
    assert "개선 제안 1건" in result["summary"]
    assert result["issues"][0]["title"] in result["summary"]
    assert result["limitations"] == "미제공 문맥"


def test_questions_are_not_promoted_to_confirmed_findings():
    result = review([item("입력 정화가 보장되나요?", question=True)])
    assert "추가 확인 1건" in result["summary"]
    assert "개선 제안" not in result["summary"]
    assert result["issues"] == [] and len(result["questions"]) == 1


def test_empty_result_is_scope_limited_and_cannot_amplify_model_claim():
    result = review([], summary="보안 취약점이 확실합니다.")
    assert "제공된 코드 범위" in result["summary"]
    assert "확인하지 못한 내용" in result["summary"]
    assert "취약점" not in result["summary"]


def test_priority_and_three_title_limit_do_not_mutate_findings_or_drop_counts():
    items = [
        item("질문", question=True),
        item("참고", "INFO"),
        item("첫 주의", "WARNING"),
        item("오류", "ERROR"),
        item("둘째 주의", "WARNING"),
    ]
    result = review(items)
    assert "개선 제안 4건 · 추가 확인 1건" in result["summary"]
    assert result["summary"].endswith("오류 / 첫 주의 / 둘째 주의")
    assert [i["title"] for i in result["issues"]] == ["참고", "첫 주의", "오류", "둘째 주의"]
    long = review([item("가" * 160) for _ in range(10)])
    assert len(long["summary"]) < 1600


def test_titles_remain_plain_text_and_whitespace_is_collapsed():
    result = review([item("<b>확인</b>\n  조건")])
    assert "<b>확인</b> 조건" in result["summary"]  # Rendered with existing Vue text interpolation.
    assert result["issues"][0]["title"] == "<b>확인</b>\n  조건"


@pytest.mark.parametrize("summary", [[], "", "x" * 1601, "password='sensitive_value'"])
def test_unused_model_summary_still_must_pass_existing_schema_and_secret_checks(summary):
    with pytest.raises(ValueError):
        review([], summary=summary)
