"""Tenant-scoped immutable snapshots exported to the review domain."""

from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.standards import repository as store
from app.domain.standards.index import MAX_CONTEXT, Rule, matches, retrieve
from app.domain.standards.service import error


@dataclass(frozen=True)
class StandardSnapshot:
    id: UUID
    document_id: UUID
    version: int
    title: str
    kind: str
    include: list[str]
    exclude: list[str]
    required: bool
    rules: list[Rule]
    sections: list[dict[str, object]]


async def snapshot(
    s: AsyncSession, wid: UUID, repo: UUID, ids: list[str] | None = None
) -> list[StandardSnapshot]:
    # Caller already holds the workspace lock and authorizes the repository.
    rows = await store.snapshots(s, wid, repo, ids)
    if not rows or (ids is not None and len(rows) != len(ids)):
        raise error(
            "STANDARDS_UNAVAILABLE", "활성 팀 문서를 등록하거나 삭제·비활성화 여부를 확인해 주세요."
        )
    return [
        StandardSnapshot(
            r.id,
            r.document_id,
            r.version,
            r.title,
            r.kind,
            cast(list[str], r.config["include"]),
            cast(list[str], r.config["exclude"]),
            bool(r.config["required"]),
            [Rule.model_validate(rule) for rule in cast(list[object], r.config["rules"])],
            r.sections,
        )
        for r in rows
    ]


def context(
    documents: list[StandardSnapshot],
    paths: dict[str, str],
    query: str,
    max_bytes: int = MAX_CONTEXT,
) -> dict[str, object]:
    candidates: list[dict[str, object]] = []
    for doc in documents:
        file_ids = [
            fid
            for fid, path in paths.items()
            if matches(path, doc.include) and not matches(path, doc.exclude)
        ]
        if not file_ids:
            continue
        for section in doc.sections:
            candidates.append(
                {
                    "id": f"{doc.id}:{section['id']}",
                    "document_id": str(doc.document_id),
                    "version_id": str(doc.id),
                    "version": doc.version,
                    "title": doc.title,
                    "kind": doc.kind,
                    "section": section["id"],
                    "heading": section["heading"],
                    "text": section["text"],
                    "_terms": section["terms"],
                    "required": doc.required,
                    "file_ids": file_ids,
                }
            )
    result = retrieve(candidates, query, max_bytes)
    result["documents"] = [
        {
            "document_id": str(d.document_id),
            "version_id": str(d.id),
            "version": d.version,
            "title": d.title,
            "kind": d.kind,
        }
        for d in documents
    ]
    return result


def check_rules(
    documents: list[StandardSnapshot], paths: dict[str, str], files: list[dict[str, object]]
) -> list[dict[str, object]]:
    from app.domain.analysis.api import import_references

    reports: list[dict[str, object]] = []
    by_id = {str(f["file_id"]): f for f in files}
    for doc in documents:
        for index, rule in enumerate(doc.rules):
            section = next(s for s in doc.sections if s["id"] == rule.section)
            for fid, path in paths.items():
                if (
                    not matches(path, doc.include)
                    or matches(path, doc.exclude)
                    or not matches(path, rule.include)
                    or matches(path, rule.exclude)
                ):
                    continue
                violation, line, limited = False, None, False
                if rule.kind == "NAME_SUFFIX":
                    violation = not path.rsplit("/", 1)[-1].endswith(rule.value)
                elif rule.kind == "PATH_PREFIX":
                    violation = not path.startswith(rule.value.rstrip("/") + "/")
                else:
                    lines = cast(list[dict[str, object]], by_id[fid]["lines"])
                    references = import_references(
                        path, [(cast(int, v["line"]), str(v["code"])) for v in lines]
                    )
                    changed = {v["line"] for v in lines if v["changed"]}
                    hits = [
                        (n, target)
                        for n, target in references
                        if n in changed
                        and (
                            target == rule.value
                            or target.startswith(rule.value.rstrip("./") + ".")
                            or target.startswith(rule.value.rstrip("./") + "/")
                        )
                    ]
                    violation, line, limited = bool(hits), hits[0][0] if hits else None, True
                reports.append(
                    {
                        "rule": f"{doc.id}:r{index + 1}",
                        "kind": rule.kind,
                        "value": rule.value,
                        "file_id": fid,
                        "file_path": path,
                        "line": line,
                        "status": "VIOLATION" if violation else "LIMITED" if limited else "CHECKED",
                        "citation": {
                            "document_id": str(doc.document_id),
                            "version": doc.version,
                            "title": doc.title,
                            "section": rule.section,
                            "heading": section["heading"],
                        },
                    }
                )
    return reports
