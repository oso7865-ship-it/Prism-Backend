"""Render narrow, supplied assertion mismatches without a fallible causal paraphrase."""

import json
from typing import TYPE_CHECKING, Any, cast

from app.domain.review.path_observations import path_facts

if TYPE_CHECKING:
    from app.domain.review.policy import InputBundle


def value_label(value: object) -> str:
    # Do not persist literal project strings, dictionaries or argument data.
    if value is None:
        return "None"
    if type(value) is bool:
        return "True" if value else "False"
    if type(value) is int:
        return str(value)
    if type(value) is str:
        return "빈 문자열" if value == "" else "비어 있지 않은 문자열"
    if type(value) is list:
        return f"원소 {len(value)}개의 리스트"
    return "값"


def ground_assertions(result: dict[str, Any], bundle: "InputBundle") -> dict[str, Any]:
    from app.domain.review.policy import result_summary, validate_result

    context = json.loads(bundle.payload)
    if context.get("purpose", "CODE") != "CODE":
        return result
    files = {f["file_id"]: f for f in context["files"]}
    derived: list[dict[str, Any]] = []
    for fact in path_facts(bundle.payload):
        fid = str(fact["file_id"])
        file = files[fid]
        changed = {r["line"] for r in file["lines"] if r["changed"]}
        if file.get("role", "changed") != "changed" or not changed:
            continue
        examples = cast(list[dict[str, Any]], fact["observations"])
        mismatches = [
            o
            for o in examples
            if o.get("matches_assertion") is False and changed & set(o.get("visited_lines", []))
        ]
        if not mismatches:
            continue
        # Group supplied tests of the same changed pure operation; never infer other inputs.
        for observation in mismatches[:2]:
            touched = changed & set(observation["visited_lines"])
            line = min(touched)
            if any(i["file_id"] == fid and i["line"] == line for i in derived):
                continue
            refs = sorted({line, observation["test_line"]})
            if len(derived) >= 4:
                break
            expected = value_label(observation["asserted_value"])
            observed = value_label(observation["value"])
            branches = ", ".join(
                f"{b['line']}줄 조건 {'참' if b['condition'] else '거짓'}"
                for b in observation["branches"][:6]
            )
            derived.append(
                {
                    "file_id": fid,
                    "line": line,
                    "severity": "WARNING",
                    "basis": "SUPPORTED",
                    "evidence_lines": refs,
                    "assumptions": [],
                    "title": f"{line}줄 처리에서 테스트의 기대값과 코드 계산이 달라요",
                    "trigger": (
                        f"제공된 {observation['test_line']}줄 단언의 입력과 "
                        "함수 기본값을 적용하는 경우"
                    ),
                    "consequence": (
                        f"지원하는 순수 코드 구간을 계산하면 {observed}이지만, "
                        f"단언은 {expected}을 요구해요."
                    ),
                    "evidence": f"{branches or '지원하는 순수 반환식'}을 따라 계산한 결과예요. "
                    "테스트 실행 결과는 아니며 다른 입력은 포함하지 않았어요.",
                    "suggestion": (
                        f"{line}줄의 값 처리와 "
                        f"{observation['test_line']}줄의 기대값을 함께 확인하세요. "
                        "의도한 계약에 맞게 수정하고 기존 정상 입력도 유지되는지 테스트하세요. "
                        "이 차이를 해결하는 구체적 수정 코드는 아직 검증하지 않았어요."
                    ),
                }
            )
    if not derived:
        return result
    checked = validate_result(
        json.dumps(
            {
                "summary": "코드 계산",
                "issues": derived,
                "limitations": "지원하는 순수 구간의 제한 계산",
            },
            ensure_ascii=False,
        ),
        bundle,
    )
    added, omitted = [], 0
    for item in cast(list[dict[str, Any]], checked["issues"]):
        remaining = {
            key: [
                i
                for i in result[key]
                if (i["file_path"], i["line"]) != (item["file_path"], item["line"])
            ]
            for key in ("issues", "questions")
        }
        if sum(len(v) for v in remaining.values()) >= 10:
            omitted += 1
            continue
        # This narrow, independently computed observation owns its exact anchor only.
        result.update(remaining)
        item["origin"] = "STATIC_PROJECTION"
        result["issues"].append(item)
        added.append(item["file_path"])
    result["summary"] = result_summary(result["issues"], result["questions"])
    result["grounding"] = {"status": "BOUNDED", "findings": len(added), "omitted": omitted}
    if omitted:
        result["limitations"] += " 결과 한도로 일부 독립 계산 차이를 표시하지 못했어요."
    for check in result.get("verification", {}).get("file_checks", []):
        if bundle.anchors[check["file_id"]][0] in added:
            check["outcome"] = "FINDING"
            check["observation"] = (
                "제공된 단언의 기대값과 제한된 코드 계산이 달라요. 테스트 실행 결과는 아니에요."
            )
    return result
