import hashlib
import json
import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.domain.review.harness import version

POLICY = "BOUNDED_CODE_V4"
MAX_FILE = 16384
MAX_INPUT = 49152
SECRET = re.compile(
    "-----BEGIN [A-Z ]*PRIVATE KEY|(?:gh[pousr]_[A-Za-z0-9]{15,}|"
    "github_pat_[A-Za-z0-9_]{15,}|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0"
    "-9]{16})|(?:password|secret|api[_-]?key|token)\\s*[:=]\\s*[\\\"'"
    "][^\\\"'\\r\\n]{4,}[\\\"']",
    re.I,
)


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    file_id: str = Field(
        max_length=8, description="Changed file containing the reported operation."
    )
    line: int = Field(ge=1, description="Provided HEAD line in this item's file_id.")
    severity: Literal["INFO", "WARNING", "ERROR"]
    basis: Literal["SUPPORTED", "NEEDS_CONTEXT"]
    evidence_lines: list[int] = Field(
        min_length=1,
        max_length=8,
        description=(
            "Unique provided lines ONLY in this item's file_id; include line and a changed line. "
            "NEVER mix related-file line numbers here. "
            "Cite related file IDs/lines in evidence text."
        ),
    )
    trigger: str = Field(min_length=1, max_length=400)
    consequence: str = Field(min_length=1, max_length=400)
    assumptions: list[str] = Field(max_length=3)
    title: str = Field(min_length=1, max_length=160)
    evidence: str = Field(min_length=1, max_length=800)
    suggestion: str = Field(min_length=1, max_length=800)


class ReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=1600)
    issues: list[Issue] = Field(max_length=10)
    limitations: str = Field(min_length=1, max_length=1600)


def issue_key(issue: dict[str, object]) -> str:
    """Heuristic identity, never proof that two findings are semantically equal."""
    value = f"{issue.get('file_path', '')}\0{' '.join(str(issue.get('title', '')).lower().split())}"
    return hashlib.sha256(value.encode()).hexdigest()


PROMPT = version(ReviewOutput.model_json_schema())


@dataclass
class InputBundle:
    payload: str
    anchors: dict[str, tuple[str, set[int]]]
    omitted: int
    coverage: dict[str, object]


def exclusion(
    path: object, patch: object, ignored: list[str], per_file: int = MAX_FILE
) -> str | None:
    if (
        not isinstance(path, str)
        or len(path.encode()) > 4096
        or any(p in ("", ".", "..") for p in path.split("/"))
        or "\\" in path
        or any(ord(c) < 32 for c in path)
    ):
        return "INVALID_PATH"
    if SECRET.search(path):
        return "SENSITIVE_PATH"
    if not path.endswith((".java", ".py", ".js", ".jsx", ".ts", ".tsx")):
        return "UNSUPPORTED_LANGUAGE"
    if any(fnmatchcase(path, pattern) for pattern in ignored) or any(
        part.lower() in ("secrets", "credentials", "node_modules", "vendor")
        for part in path.split("/")
    ):
        return "EXCLUDED_PATH"
    if not isinstance(patch, str):
        return "PATCH_UNAVAILABLE"
    if SECRET.search(patch):
        return "SECRET_SUSPECTED"
    if len(patch.encode()) > per_file:
        return "PATCH_TOO_LARGE"
    return None


def prepare(
    changes: list[dict[str, object]],
    findings: list[dict[str, object]],
    ignored: list[str],
    total_files: int | None = None,
    *,
    per_file: int = MAX_FILE,
    max_input: int = MAX_INPUT,
) -> InputBundle:
    files: list[dict[str, object]] = []
    anchors: dict[str, tuple[str, set[int]]] = {}
    excluded: list[dict[str, object]] = []
    changes = changes[:100]
    for change in changes:
        path, patch = change.get("filename"), change.get("patch")
        reason = exclusion(path, patch, ignored, per_file)
        if reason or len(files) >= 8:
            excluded.append(
                {
                    "file_path": None if reason in ("INVALID_PATH", "SENSITIVE_PATH") else path,
                    "reason": reason or "FILE_LIMIT",
                }
            )
            continue
        assert isinstance(path, str) and isinstance(patch, str)
        # Only HEAD-side context/additions. Removed lines never become false HEAD anchors.
        lines: list[dict[str, object]] = []
        number = 0
        for line in patch.splitlines():
            match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if match:
                number = int(match[1])
            elif number and line.startswith(("+", " ")):
                lines.append({"line": number, "code": line[1:], "changed": line.startswith("+")})
                number += 1
        if not lines:
            excluded.append({"file_path": path, "reason": "NO_HEAD_LINES"})
            continue
        fid = f"f{len(files) + 1}"
        item: dict[str, object] = {
            "file_id": fid,
            "language": path.rsplit(".", 1)[-1],
            "lines": lines,
        }
        trial = json.dumps(
            {"files": [*files, item], "static_findings": findings}, ensure_ascii=False
        )
        if len(json.dumps(item, ensure_ascii=False).encode()) > per_file:
            excluded.append({"file_path": path, "reason": "PATCH_TOO_LARGE"})
            continue
        if len(trial.encode()) > max_input:
            excluded.append({"file_path": path, "reason": "INPUT_LIMIT"})
            continue
        files.append(item)
        anchors[fid] = (path, {cast(int, line["line"]) for line in lines})
    if not files:
        raise ValueError("NO_SAFE_CONTEXT")
    payload = json.dumps({"files": files, "static_findings": findings}, ensure_ascii=False)
    if SECRET.search(payload) or len(payload.encode()) > max_input:
        raise ValueError("UNSAFE_CONTEXT")
    coverage: dict[str, object] = {
        "files": [
            {"file_id": fid, "file_path": path, "provided_lines": len(lines)}
            for fid, (path, lines) in anchors.items()
        ],
        "excluded": excluded,
        "unfetched_files": max(0, total_files - len(changes)) if total_files is not None else None,
    }
    return InputBundle(payload, anchors, len(excluded), coverage)


def result_summary(issues: list[dict[str, object]], questions: list[dict[str, object]]) -> str:
    """Describe accepted items without a second, potentially contradictory model assessment."""
    if not issues and not questions:
        return (
            "제공된 코드 범위에서 지적할 항목을 찾지 못했어요. "
            "검토 범위와 확인하지 못한 내용을 함께 살펴보세요."
        )
    counts = []
    if issues:
        counts.append(f"개선 제안 {len(issues)}건")
    if questions:
        counts.append(f"추가 확인 {len(questions)}건")
    parts = [" · ".join(counts) + "이 있어요."]
    priority = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    remaining = 3
    for label, items in (("먼저 검토할 제안", issues), ("추가 확인할 내용", questions)):
        selected = sorted(items, key=lambda i: priority[str(i["severity"])])[:remaining]
        if selected:
            parts.append(
                label + ": " + " / ".join(" ".join(str(i["title"]).split()) for i in selected)
            )
            remaining -= len(selected)
    return "\n".join(parts)


def validate_result(raw: str, bundle: InputBundle) -> dict[str, object]:
    if len(raw.encode()) > 24000 or SECRET.search(raw):
        raise ValueError("INVALID_OUTPUT")
    output = ReviewOutput.model_validate_json(raw)
    files = {f["file_id"]: f for f in json.loads(bundle.payload)["files"]}
    issues: list[dict[str, object]] = []
    questions: list[dict[str, object]] = []
    for issue in output.issues:
        if issue.basis == "NEEDS_CONTEXT" and issue.severity == "ERROR":
            raise ValueError("UNSUPPORTED_SEVERITY")
        anchor = bundle.anchors.get(issue.file_id)
        if not anchor or issue.line not in anchor[1]:
            raise ValueError("INVALID_OUTPUT_LOCATION")
        refs = set(issue.evidence_lines)
        changed = {line["line"] for line in files[issue.file_id]["lines"] if line["changed"]}
        if (
            len(refs) != len(issue.evidence_lines)
            or issue.line not in refs
            or not refs <= anchor[1]
            or not refs & changed
        ):
            raise ValueError("INVALID_EVIDENCE_LINES")
        if any(not s.strip() or len(s) > 400 for s in issue.assumptions):
            raise ValueError("INVALID_ASSUMPTIONS")
        if (issue.basis == "SUPPORTED") != (not issue.assumptions):
            raise ValueError("INCONSISTENT_EVIDENCE_BASIS")
        if not issue.trigger.strip() or not issue.consequence.strip():
            raise ValueError("EMPTY_EVIDENCE")
        entry = {**issue.model_dump(exclude={"file_id"}), "file_path": anchor[0]}
        entry["key"] = issue_key(entry)
        (issues if issue.basis == "SUPPORTED" else questions).append(entry)
    return {
        "summary": result_summary(issues, questions),
        "issues": issues,
        "questions": questions,
        "classification": "SUPPORTED_FINDINGS_AND_CONTEXT_QUESTIONS",
        "limitations": output.limitations,
        "reviewed_files": len(bundle.anchors),
        "omitted_files": bundle.omitted,
        "coverage": bundle.coverage,
        "scope": (
            "고정 HEAD의 제공 줄과 제한된 관련 문맥만 검토. 전체 호출 경로·실행 결과는 미검증."
        ),
    }
