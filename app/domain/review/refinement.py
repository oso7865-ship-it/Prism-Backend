"""Bounded second-pass contracts shared by workers and evaluation."""

import json

from app.domain.review.dictionary_observations import dictionary_facts
from app.domain.review.empty_review import validate_file_checks
from app.domain.review.grounded_claims import ground_assertions
from app.domain.review.path_observations import path_facts
from app.domain.review.policy import MAX_INPUT, InputBundle, ReviewOutput, validate_result
from app.domain.review.semantics import facts
from app.domain.review.verification import VerificationOutput, apply_verification


def add_observations(bundle: InputBundle) -> None:
    observations = facts(bundle.payload)
    dictionaries = dictionary_facts(bundle.payload)
    covered = {(item["file_id"], item["line"]) for item in dictionaries}
    observations = [item for item in observations if (item["file_id"], item["line"]) not in covered]
    observations += dictionaries
    paths = path_facts(bundle.payload)
    # The path projection already includes operator results and actual supplied arguments.
    # Remove redundant illustrative operations, never source or unrelated observations.
    projected = {p["file_id"] for p in paths}
    observations = [item for item in observations if item["file_id"] not in projected]
    if not observations and not paths:
        return
    data = json.loads(bundle.payload)
    data["semantic_observations"] = observations
    if paths:
        data["path_observations"] = paths
    encoded = json.dumps(data, ensure_ascii=False)
    if len(encoded.encode()) <= MAX_INPUT:
        bundle.payload = encoded


def independent_result(
    bundle: InputBundle,
    signals: list[dict[str, object]],
) -> dict[str, object] | None:
    if not signals:
        return None
    return {
        "summary": "AI 답변을 완료하지 못했어요. 별도로 발견한 보안 신호는 확인할 수 있어요.",
        "issues": [],
        "questions": [],
        "purpose": "SECURITY",
        "limitations": "AI 검토 미완료. 별도 코드 규칙의 제공 범위만 확인했어요.",
        "scope": "제공된 직선 코드 구간만 검사. 전체 경로와 실행 결과는 미확인.",
        "reviewed_files": len(bundle.anchors),
        "omitted_files": bundle.omitted,
        "coverage": bundle.coverage,
        "security_evidence": [
            {**item, "file_path": bundle.anchors[str(item["file_id"])][0]} for item in signals
        ],
    }


def verified_result(raw: str, draft: str, bundle: InputBundle) -> dict[str, object]:
    revised, metadata = apply_verification(raw, draft)
    result = validate_result(revised, bundle)
    checks = VerificationOutput.model_validate_json(raw).file_checks
    metadata["file_checks"] = validate_file_checks(
        checks,
        ReviewOutput.model_validate_json(revised),
        bundle,
    )
    metadata.setdefault("added", 0)
    result["verification"] = metadata
    return ground_assertions(result, bundle)


def needs_reasoning(payload: str) -> bool:
    """A reproducible experiment selector, never model self-reported confidence."""
    data = json.loads(payload)
    context = data.get("context", data)
    if context.get("semantic_observations") or context.get("context_supplement"):
        return True
    branch_count = sum(
        any(word in row["code"] for word in ("if ", "else", "?", "&&", "||"))
        for file in context["files"]
        for row in file["lines"]
    )
    return branch_count >= 4
