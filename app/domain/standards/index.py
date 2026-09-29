"""Bounded document indexing and lexical retrieval. Never execute uploaded content."""

import hashlib
import json
import math
import re
from collections import Counter
from fnmatch import fnmatchcase
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_CONTEXT = 12 * 1024


def matches(path: str, patterns: list[str]) -> bool:
    return any(
        fnmatchcase(path, p) or (p.startswith("**/") and fnmatchcase(path, p[3:])) for p in patterns
    )


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["NAME_SUFFIX", "PATH_PREFIX", "FORBIDDEN_IMPORT"]
    value: str = Field(min_length=1, max_length=160)
    section: str = Field(pattern=r"^s[1-9][0-9]{0,3}$")
    include: list[str] = Field(default_factory=lambda: ["**"], min_length=1, max_length=8)
    exclude: list[str] = Field(default_factory=list, max_length=8)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    kind: Literal["CONVENTION", "STRUCTURE"]
    content: str = Field(min_length=1, max_length=65536)
    include: list[str] = Field(default_factory=lambda: ["**"], min_length=1, max_length=8)
    exclude: list[str] = Field(default_factory=list, max_length=8)
    required: bool = False
    rules: list[Rule] = Field(default_factory=list, max_length=20)
    expected_version: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def safe(self) -> "DocumentInput":
        from app.shared.content_safety import SECRET

        if (
            not self.title.strip()
            or not self.content.strip()
            or len(self.content.encode()) > 65536
            or any(ord(c) < 32 and c not in "\n\r\t" for c in self.content)
            or SECRET.search(self.model_dump_json())
        ):
            raise ValueError("문서는 비밀정보가 없는 UTF-8 텍스트 64KiB 이하여야 합니다.")
        patterns = [*self.include, *self.exclude]
        for rule in self.rules:
            patterns.extend([*rule.include, *rule.exclude])
            if any(ord(c) < 32 for c in rule.value) or "\\" in rule.value:
                raise ValueError("규칙 값이 올바르지 않습니다.")
        if any(
            not p
            or len(p) > 160
            or "\\" in p
            or p.startswith("/")
            or ".." in p.split("/")
            or any(ord(c) < 32 for c in p)
            for p in patterns
        ):
            raise ValueError("저장소 안의 상대 경로 패턴을 사용해 주세요.")
        ids = {s["id"] for s in index_document(self.content)}
        if not ids:
            raise ValueError("제목 아래에 규칙 내용을 입력해 주세요.")
        if any(rule.section not in ids for rule in self.rules):
            raise ValueError("규칙의 근거 섹션을 선택해 주세요.")
        return self


def terms(value: str) -> list[str]:
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    tokens = re.findall(r"[a-zA-Z0-9_]+|[가-힣]+", value.lower())
    # Korean bigrams handle common particles without downloading a tokenizer/model.
    return [
        t
        for token in tokens
        for t in (
            [token] + [token[i : i + 2] for i in range(len(token) - 1)]
            if re.fullmatch(r"[가-힣]{3,}", token)
            else [token]
        )
    ]


def index_document(content: str) -> list[dict[str, object]]:
    sections: list[dict[str, object]] = []
    title = "문서"
    lines: list[str] = []

    def flush() -> None:
        body = "\n".join(lines).strip()
        for start in range(0, len(body), 1200):
            text = body[start : start + 1200]
            sections.append(
                {
                    "id": f"s{len(sections) + 1}",
                    "heading": title,
                    "text": text,
                    "terms": dict(Counter(terms(title + " " + text))),
                }
            )

    fenced = False
    for line in content.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        heading = re.match(r"^#{1,6}\s+(.+)$", line) if not fenced else None
        if heading:
            flush()
            title, lines = heading[1][:160], []
        else:
            lines.append(line)
    flush()
    return sections


def digest(body: DocumentInput) -> str:
    return hashlib.sha256(body.model_dump_json(exclude={"expected_version"}).encode()).hexdigest()


def retrieve(
    candidates: list[dict[str, object]], query: str, max_bytes: int = MAX_CONTEXT
) -> dict[str, object]:
    """All required sections first; fail closed on their overflow, report optional omissions."""
    query_terms = set(terms(query))
    counts = [
        Counter(cast(dict[str, int], s["_terms"]))
        if "_terms" in s
        else Counter(terms(str(s["heading"]) + " " + str(s["text"])))
        for s in candidates
    ]
    avg = sum(sum(c.values()) for c in counts) / max(len(counts), 1) or 1
    df = Counter(t for c in counts for t in c)
    scored = []
    for i, (item, count) in enumerate(zip(candidates, counts, strict=True)):
        length = sum(count.values())
        score = sum(
            math.log(1 + (len(counts) - df[t] + 0.5) / (df[t] + 0.5))
            * count[t]
            * 2.2
            / (count[t] + 1.2 * (0.25 + 0.75 * length / avg))
            for t in query_terms
            if count[t]
        )
        scored.append((item, score, i))
    scored.sort(key=lambda s: (not bool(s[0]["required"]), -s[1], s[2]))
    scope_fallback = bool(scored) and not any(
        item["required"] or score > 0 for item, score, _ in scored
    )
    chosen: list[dict[str, object]] = []
    for item, score, _ in scored:
        if not item["required"] and ((score <= 0 and not scope_fallback) or len(chosen) >= 12):
            continue
        wire = {k: v for k, v in item.items() if k != "_terms"}
        if len(json.dumps([*chosen, wire], ensure_ascii=False).encode()) > min(
            max_bytes, MAX_CONTEXT
        ):
            if item["required"]:
                raise ValueError("STANDARDS_REQUIRED_TOO_LARGE")
            continue
        chosen.append(wire)
    return {
        "sections": chosen,
        "candidate_count": len(candidates),
        "omitted_sections": len(candidates) - len(chosen),
        "method": "PATH_BM25_V1",
        "scope_fallback": scope_fallback,
    }
