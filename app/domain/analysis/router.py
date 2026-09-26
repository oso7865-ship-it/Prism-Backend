from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.analysis.contracts import RULE_SET, RULES
from app.domain.analysis.models import AnalysisFileResult, AnalysisRun, Finding
from app.domain.analysis.service import AnalysisService
from app.domain.auth.api import AuthAPI, CurrentPrincipal


class StartAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pr_id: UUID
    rerun_of: UUID | None = None


def view(row: AnalysisRun | Finding | AnalysisFileResult) -> dict[str, object]:
    # Explicit response allowlists: no ORM serializer or arbitrary JSON body forwarding.
    fields = {
        AnalysisRun: (
            "id pr_id repository_connection_id base_sha head_sha rule_set_vers"
            "ion generation status coverage_status coverage_reason total_files"
            " included_files excluded_files failed_files not_evaluated_rules f"
            "inding_count started_at finished_at error_code created_at request"
            "ed_by"
        ),
        Finding: (
            "id rule_id rule_version category severity confidence language fil"
            "e_path start_line end_line side scope_location message_code sanit"
            "ized_message fingerprint"
        ),
        AnalysisFileResult: (
            "id file_path side language source_sha status reason_code finding_"
            "limit_reached rule_outcomes"
        ),
    }
    return {name: getattr(row, name) for name in fields[type(row)].split()}


def analysis_router(engine: AsyncEngine | None, auth: AuthAPI, enabled: bool) -> APIRouter:
    router = APIRouter(prefix="/api/v1/workspaces/{wid}", tags=["analysis"])
    principal = Depends(auth.require_principal)
    service = AnalysisService(engine, enabled)

    @router.post("/analyses", status_code=202)
    async def start(
        wid: UUID, body: StartAnalysis, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        row = await service.start(p.user_id, wid, body.pr_id, body.rerun_of)
        return {
            **view(row),
            "analysis_id": row.id,
            "status_url": f"/api/v1/workspaces/{wid}/analyses/{row.id}",
        }

    @router.get("/analyses/{aid}")
    async def detail(
        wid: UUID, aid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return view(await service.get(p.user_id, wid, aid))

    @router.get("/pull-requests/{pid}/analyses")
    async def history(
        wid: UUID, pid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        rows = await service.history(p.user_id, wid, pid)
        return {
            "items": [view(r) for r in rows],
            "limit": 50,
            "rule_set_version": RULE_SET,
            "active_rules": list(RULES),
            "runner_enabled": enabled,
        }

    @router.get("/analyses/{aid}/findings")
    async def findings(
        wid: UUID, aid: UUID, p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> dict[str, object]:
        rows = await service.results(p.user_id, wid, aid, "findings", cursor)
        return {
            "items": [view(r) for r in rows[:100]],
            "next_cursor": rows[99].id if len(rows) > 100 else None,
        }

    @router.get("/analyses/{aid}/files")
    async def files(
        wid: UUID, aid: UUID, p: Annotated[CurrentPrincipal, principal], cursor: UUID | None = None
    ) -> dict[str, object]:
        rows = await service.results(p.user_id, wid, aid, "files", cursor)
        return {
            "items": [view(r) for r in rows[:100]],
            "next_cursor": rows[99].id if len(rows) > 100 else None,
        }

    @router.post("/analyses/{aid}/cancel", status_code=202)
    async def cancel(
        wid: UUID, aid: UUID, p: Annotated[CurrentPrincipal, principal]
    ) -> dict[str, object]:
        return view(await service.cancel(p.user_id, wid, aid))

    return router
