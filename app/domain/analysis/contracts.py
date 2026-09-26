import hashlib
import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

RULE_SET = "static-1.0.0"
MAX_FILE = 200 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_FILES = 100


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def build_digest() -> str:
    # Changes to executable analyzer modules or installed grammar versions invalidate reuse.
    from importlib.metadata import version
    from pathlib import Path

    root = Path(__file__).parent
    return digest(
        {
            "sources": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(root.glob("*.py"))
            },
            "parsers": {
                name: version(name)
                for name in (
                    "tree-sitter",
                    "tree-sitter-java",
                    "tree-sitter-python",
                    "tree-sitter-javascript",
                    "tree-sitter-typescript",
                )
            },
        }
    )


@dataclass(frozen=True)
class Rule:
    id: str
    message: str
    category: str = "MAINTAINABILITY"
    severity: str = "WARNING"
    confidence: str = "HIGH"
    version: str = "1.0.0"


RULES = {
    r.id: r
    for r in [
        Rule(
            "COM-001",
            "파일이 500줄을 초과합니다. 물리적 줄 수 기준의 유지보수 신호입니다.",
            severity="INFO",
        ),
        Rule(
            "COM-002", "함수 또는 메서드가 60줄을 초과합니다. 주석을 포함한 선언 범위 기준입니다."
        ),
        Rule("COM-004", "선언 인수가 5개를 초과합니다. 역할 분리를 검토하세요."),
        Rule(
            "COM-009",
            "알려진 credential 형식이 발견되었습니다. 유효성은 미검증이며 값은 저장하지 않습니다.",
            "SECURITY",
            "CRITICAL",
            "MEDIUM",
        ),
        Rule(
            "COM-010",
            "Private key 블록 형식이 발견되었습니다. 유효성은 미검증이며 값은 저장하지 않습니다.",
            "SECURITY",
            "CRITICAL",
        ),
        Rule(
            "JAVA-004",
            "비어 있거나 주석만 있는 catch 블록입니다. 예외 처리 의도를 확인하세요.",
            "RELIABILITY",
        ),
        Rule(
            "JAVA-005", "Wildcard import가 있습니다. 명시적 import를 검토하세요.", "STYLE", "INFO"
        ),
        Rule(
            "JAVA-006",
            "빈 statement를 본문으로 가진 반복문입니다. 의도적인 대기인지 확인하세요.",
            "RELIABILITY",
        ),
        Rule(
            "JAVA-007",
            "public static이며 final이 아닌 필드입니다. 공유 상태 변경을 검토하세요.",
            "RELIABILITY",
        ),
        Rule(
            "JAVA-008",
            "문자열 literal에 == 또는 !=를 사용했습니다. 의도적인 참조 비교인지 확인하세요.",
            "RELIABILITY",
            confidence="MEDIUM",
        ),
        Rule(
            "PY-001",
            "변경 가능한 literal 기본 인수입니다. 호출 간 공유 의도를 확인하세요.",
            "RELIABILITY",
        ),
        Rule(
            "PY-002",
            "예외 타입이 없는 except입니다. 시스템 예외까지 포착할 수 있습니다.",
            "RELIABILITY",
        ),
        Rule(
            "PY-003", "pass만 있는 except 본문입니다. 오류 무시 의도를 확인하세요.", "RELIABILITY"
        ),
        Rule("PY-006", "Wildcard import가 있습니다. 명시적 import를 검토하세요.", "STYLE", "INFO"),
        Rule("JS-001", "var 선언입니다. let 또는 const 사용을 검토하세요.", "STYLE", "INFO"),
        Rule("JS-002", "느슨한 동등 비교입니다. 타입 강제 변환 의도를 확인하세요.", "RELIABILITY"),
        Rule(
            "JS-003", "debugger statement가 있습니다. 개발 잔여 코드인지 확인하세요.", "RELIABILITY"
        ),
        Rule(
            "JS-004",
            "비어 있거나 주석만 있는 catch 블록입니다. 예외 처리 의도를 확인하세요.",
            "RELIABILITY",
        ),
        Rule("TS-001", "명시적 any 타입입니다. 이 경계의 타입 검증 의도를 확인하세요."),
        Rule("TS-002", "@ts-ignore 지시 주석입니다. 타입 검사 우회 사유를 확인하세요."),
        Rule("TS-003", "@ts-nocheck 지시 주석입니다. 파일 타입 검사가 비활성화됩니다."),
        Rule(
            "TS-004",
            "Non-null assertion입니다. null이 불가능한지 사람이 확인해야 합니다.",
            "RELIABILITY",
            confidence="MEDIUM",
        ),
        Rule(
            "TS-005",
            "unknown 또는 any를 거치는 이중 타입 assertion입니다. 타입 안전성을 확인하세요.",
            confidence="MEDIUM",
        ),
    ]
}


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str | None = None
    status: str
    reason: str | None = None
    findings: list[Observation] = Field(default_factory=list, max_length=100)
    evaluated: list[str] = Field(default_factory=list)
    not_evaluated: list[str] = Field(default_factory=list)
    limit: bool = False


def language_for(path: str) -> str | None:
    ext = path.rsplit(".", 1)[-1].lower()
    return {
        "java": "JAVA",
        "py": "PYTHON",
        "js": "JAVASCRIPT",
        "jsx": "JAVASCRIPT",
        "mjs": "JAVASCRIPT",
        "cjs": "JAVASCRIPT",
        "ts": "TYPESCRIPT",
        "tsx": "TYPESCRIPT",
        "mts": "TYPESCRIPT",
        "cts": "TYPESCRIPT",
    }.get(ext)


def applicable(language: str | None) -> list[str]:
    prefixes = {
        "JAVA": ("JAVA-",),
        "PYTHON": ("PY-",),
        "JAVASCRIPT": ("JS-",),
        "TYPESCRIPT": ("JS-", "TS-"),
    }.get(language or "", ())
    return [
        r
        for r in RULES
        if r in ("COM-009", "COM-010")
        or (language and (r.startswith("COM-") or r.startswith(prefixes)))
    ]
