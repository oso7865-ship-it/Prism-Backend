"""Read-only, tenant-authorized snapshot exported to the review domain."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analysis.models import Finding
from app.domain.analysis.service import authorized, error


def import_references(path: str, lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Syntax-only references on provided lines. Gaps/unsupported imports are not coverage."""
    import re

    from app.domain.analysis.analyzer import parser_for
    from app.domain.analysis.contracts import language_for

    language = language_for(path)
    if language not in {"JAVA", "PYTHON", "JAVASCRIPT", "TYPESCRIPT"} or not lines:
        return []
    numbered = {n: code for n, code in lines if 0 < n <= 200_000}
    if not numbered:
        return []
    data = "\n".join(numbered.get(n, "") for n in range(1, max(numbered) + 1)).encode()
    tree = parser_for(language, path).parse(data)
    references: list[tuple[int, str]] = []
    pending = [tree.root_node]
    while pending:
        node = pending.pop()
        if node.type in {"import_statement", "import_from_statement", "import_declaration"}:
            if node.has_error:
                continue
            text = data[node.start_byte : node.end_byte].decode()
            line = node.start_point.row + 1
            if language == "PYTHON":
                import ast

                try:
                    stmt = ast.parse(text).body[0]
                except (SyntaxError, ValueError):
                    continue
                if isinstance(stmt, ast.Import):
                    references.extend((line, name.name) for name in stmt.names)
                elif isinstance(stmt, ast.ImportFrom) and stmt.module:
                    references.append((line, "." * stmt.level + stmt.module))
            elif language == "JAVA":
                target = re.match(r"import\s+(?:static\s+)?([\w.*]+)", text)
                if target:
                    references.append((line, target[1].removesuffix(".*")))
            else:
                source = node.child_by_field_name("source")
                if source:
                    references.append(
                        (line, data[source.start_byte : source.end_byte].decode().strip("\"'"))
                    )
        else:
            pending.extend(node.named_children)
    return references


@dataclass(frozen=True)
class ReviewSnapshot:
    id: UUID
    pr_id: UUID
    repository_id: UUID
    connection_generation: int
    base_sha: str
    head_sha: str
    findings: list[dict[str, object]]
    config_version_id: UUID


async def require_review_read(s: AsyncSession, uid: UUID, wid: UUID, aid: UUID) -> None:
    await authorized(s, uid, wid, aid)


async def review_snapshot(s: AsyncSession, uid: UUID, wid: UUID, aid: UUID) -> ReviewSnapshot:
    row = await authorized(s, uid, wid, aid, active=True)
    if row.status != "COMPLETED":
        raise error("ANALYSIS_NOT_COMPLETED")
    findings = list(
        (
            await s.scalars(
                select(Finding)
                .where(Finding.workspace_id == wid, Finding.analysis_id == aid)
                .order_by(Finding.fingerprint)
                .limit(1000)
            )
        ).all()
    )
    ranks = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}
    findings.sort(key=lambda f: ranks.get(f.severity, 4))
    safe: list[dict[str, object]] = [
        dict[str, object](
            rule_id=f.rule_id, severity=f.severity, language=f.language, message=f.sanitized_message
        )
        for f in findings
        if f.category != "SECURITY"
    ][:10]
    return ReviewSnapshot(
        row.id,
        row.pr_id,
        row.repository_connection_id,
        row.connection_generation,
        row.base_sha,
        row.head_sha,
        safe,
        row.config_version_id,
    )
