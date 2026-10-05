import asyncio
import json
from datetime import UTC, datetime
from typing import cast
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.analysis.api import review_snapshot
from app.domain.pull_request.api import analysis_snapshot
from app.domain.repository.api import RepositoryAccess
from app.domain.review.context import repository_path
from app.domain.review.context_selection import enrich
from app.domain.review.empty_review import validate_empty_review
from app.domain.review.feedback import prior_feedback
from app.domain.review.harness import compose
from app.domain.review.policy import (
    MAX_INPUT,
    POLICY,
    PROMPT,
    SECRET,
    ReviewOutput,
    prepare,
    validate_result,
)
from app.domain.review.provider import Provider
from app.domain.review.refinement import add_observations, independent_result, verified_result
from app.domain.review.reranker import Ranker
from app.domain.review.security_evidence import scan as security_scan
from app.domain.review.service import TERMINAL, authorize, error, get_row
from app.domain.review.supplement import supplement
from app.domain.review.verification import verification_payload
from app.domain.standards.api import check_rules
from app.domain.standards.api import context as standards_context
from app.domain.standards.api import snapshot as standards_snapshot
from app.domain.workspace.api import WorkspaceAccess
from app.shared.database.engine import transaction
from app.shared.exception.base import AppException
from app.shared.github.client import GitHubClient, GitHubFailure
from app.shared.jobs import store as jobs
from app.shared.jobs.store import Claim


class ReviewWorker:
    def __init__(
        self,
        engine: AsyncEngine,
        github: GitHubClient,
        provider: Provider,
        ranker: Ranker | None = None,
    ) -> None:
        self.engine, self.github, self.provider = engine, github, provider
        self.ranker = ranker

    async def execute(self, c: Claim, expired: bool = False) -> None:
        if expired:
            await self.complete(c, None, "LEASE_EXPIRED", expired=True)
            return
        assert c.workspace_id
        incoming = outgoing = 0
        independent: dict[str, object] | None = None
        try:
            async with transaction(self.engine) as s:
                await WorkspaceAccess(s).lock_system(c.workspace_id)
                row = await get_row(s, c.workspace_id, c.aggregate_id)
                if row.status in TERMINAL or not await jobs.fence(s, c):
                    return
                await authorize(s, row.requested_by, row.workspace_id, row.id, True)
                if (
                    row.call_attempts
                    or row.model != self.provider.model
                    or row.policy_version != POLICY
                    or row.prompt_version != PROMPT
                ):
                    raise error("REVIEW_REPLAY_BLOCKED")
                snap = await review_snapshot(s, row.requested_by, row.workspace_id, row.analysis_id)
                repo = await RepositoryAccess(s).require(
                    row.requested_by, row.workspace_id, snap.repository_id
                )
                _, _, ignored = await RepositoryAccess(s).analysis_config(
                    row.requested_by, row.workspace_id, repo.id, snap.config_version_id
                )
                pr = await analysis_snapshot(s, row.requested_by, row.workspace_id, snap.pr_id)
                feedback = await prior_feedback(s, row)
                purpose = row.purpose
                mode = row.mode
                standards = (
                    await standards_snapshot(
                        s, row.workspace_id, snap.repository_id, row.standard_versions
                    )
                    if purpose == "STANDARDS"
                    else []
                )
                row.status, row.started_at = "RUNNING", datetime.now(UTC)
            async with asyncio.timeout(150):
                token = await self.github.installation_token(
                    repo.installation_id, repo.github_repository_id
                )
                prefix = (
                    f"/repos/{quote(repo.owner_login, safe='')}/"
                    f"{quote(repo.repository_name, safe='')}/pulls/{pr.pr_number}"
                )

                async def verify() -> int | None:
                    remote = await self.github.request("GET", prefix, token)
                    if (
                        not isinstance(remote, dict)
                        or remote.get("head", {}).get("sha") != snap.head_sha
                        or remote.get("base", {}).get("sha") != snap.base_sha
                    ):
                        raise error("SNAPSHOT_CHANGED")
                    count = remote.get("changed_files")
                    return count if type(count) is int and count >= 0 else None

                total_files = await verify()
                changes = await self.github.request(
                    "GET", prefix + "/files?per_page=100&page=1", token
                )
                if not isinstance(changes, list) or any(not isinstance(f, dict) for f in changes):
                    raise error("GITHUB_INVALID_RESPONSE")
                bundle = prepare(changes, snap.findings, ignored, total_files, review_mode=mode)
                bundle = await enrich(
                    bundle,
                    self.github,
                    token,
                    repository_path(repo.owner_login, repo.repository_name),
                    snap.head_sha,
                    ignored,
                    self.ranker,
                )
                context = json.loads(bundle.payload)
                context["untrusted_prior_feedback"] = feedback
                payload = json.dumps(context, ensure_ascii=False)
                included = (
                    bool(feedback)
                    and len(payload.encode()) <= MAX_INPUT
                    and not SECRET.search(payload)
                )
                if included:
                    bundle.payload = payload
                bundle.coverage["prior_feedback_count"] = len(feedback) if included else 0
                if purpose != "CODE":
                    context = json.loads(bundle.payload)
                    context["purpose"] = purpose
                    if purpose == "STANDARDS":
                        paths = {fid: path for fid, (path, _) in bundle.anchors.items()}
                        context["file_paths"] = paths
                        context["untrusted_standards"] = []
                        available = (
                            MAX_INPUT
                            + 12 * 1024
                            - len(json.dumps(context, ensure_ascii=False).encode())
                            - 32
                        )
                        if available < 0:
                            raise ValueError("STANDARDS_REQUIRED_TOO_LARGE")
                        knowledge = standards_context(
                            standards, paths, " ".join(paths.values()) + bundle.payload, available
                        )
                        if not knowledge["sections"]:
                            raise error("STANDARDS_NO_MATCH")
                        context["untrusted_standards"] = knowledge["sections"]
                        rule_checks = check_rules(standards, paths, context["files"])
                    bundle.payload = json.dumps(context, ensure_ascii=False)
                add_observations(bundle)
                security_evidence = security_scan(bundle.payload) if purpose == "SECURITY" else []
                independent = independent_result(bundle, security_evidence)
                await verify()
                _, harness = compose(bundle.payload, ReviewOutput.model_json_schema())
                # Commit each call reservation BEFORE external transmission.
                if not await self.reserve(c, 0):
                    return
                raw, incoming, outgoing = await self.provider.review(bundle.payload)
                recovered = False
                try:
                    result = validate_result(raw, bundle)
                    requests = ReviewOutput.model_validate_json(raw).context_requests
                except ValueError:
                    # Discard invalid output, never forward it or label an empty draft successful.
                    recovered, requests, result = True, [], None
                await verify()
                # Recheck authorization/lease before additional GitHub reads or AI transmission.
                if not await self.reserve(c, 1, incoming, outgoing):
                    return
                if requests:
                    bundle = await supplement(
                        bundle,
                        requests,
                        self.github,
                        token,
                        repository_path(repo.owner_login, repo.repository_name),
                        snap.head_sha,
                        ignored,
                    )
                    await verify()
                    if not await self.still_authorized(c):
                        return
                if result and (result["issues"] or result["questions"]):
                    checked, extra_in, extra_out = await self.provider.verify(
                        verification_payload(bundle.payload, raw)
                    )
                    incoming += extra_in
                    outgoing += extra_out
                    result = verified_result(checked, raw, bundle)
                else:
                    checked, extra_in, extra_out = await self.provider.recheck_empty(bundle.payload)
                    incoming += extra_in
                    outgoing += extra_out
                    result = validate_empty_review(checked, bundle)
                    if recovered:
                        metadata = cast(dict[str, object], result["verification"])
                        metadata["status"] = "OUTPUT_RECOVERED"
                if security_evidence:
                    result["security_evidence"] = [
                        {**item, "file_path": bundle.anchors[str(item["file_id"])][0]}
                        for item in security_evidence
                    ]
                result["harness"] = harness
                result["purpose"] = purpose
                if purpose == "STANDARDS":
                    result["standards"] = {k: v for k, v in knowledge.items() if k != "sections"}
                    result["standard_checks"] = rule_checks
                    result["standard_sources"] = [
                        {k: v for k, v in section.items() if k != "text"}
                        for section in cast(list[dict[str, object]], knowledge["sections"])
                    ]
                await self.complete(c, result, incoming=incoming, outgoing=outgoing)
        except TimeoutError:
            await self.complete(c, independent, "AI_TIMEOUT", incoming=incoming, outgoing=outgoing)
        except (GitHubFailure, AppException) as exc:
            await self.complete(c, independent, exc.code, incoming=incoming, outgoing=outgoing)
        except ValueError as exc:
            code = (
                str(exc)
                if str(exc) in {"NO_SAFE_CONTEXT", "STANDARDS_REQUIRED_TOO_LARGE"}
                else "AI_CONTEXT_OR_OUTPUT_INVALID"
            )
            await self.complete(c, independent, code, incoming=incoming, outgoing=outgoing)
        except Exception:
            # Provider exceptions can include keys, inputs or raw outputs. Never persist/log them.
            await self.complete(
                c, independent, "AI_PROVIDER_FAILED", incoming=incoming, outgoing=outgoing
            )

    async def still_authorized(self, c: Claim) -> bool:
        assert c.workspace_id
        async with transaction(self.engine) as s:
            await WorkspaceAccess(s).lock_system(c.workspace_id)
            row = await get_row(s, c.workspace_id, c.aggregate_id)
            if row.status != "RUNNING" or not await jobs.fence(s, c):
                return False
            await authorize(s, row.requested_by, row.workspace_id, row.id, True)
            return True

    async def reserve(self, c: Claim, expected: int, incoming: int = 0, outgoing: int = 0) -> bool:
        assert c.workspace_id
        async with transaction(self.engine) as s:
            await WorkspaceAccess(s).lock_system(c.workspace_id)
            row = await get_row(s, c.workspace_id, c.aggregate_id)
            row.input_tokens = max(row.input_tokens, incoming, 0)
            row.output_tokens = max(row.output_tokens, outgoing, 0)
            if (
                row.status != "RUNNING"
                or row.call_attempts != expected
                or not await jobs.fence(s, c)
            ):
                return False
            await authorize(s, row.requested_by, row.workspace_id, row.id, True)
            row.call_attempts, row.usage_uncertain = expected + 1, True
            return True

    async def complete(
        self,
        c: Claim,
        result: dict[str, object] | None,
        code: str | None = None,
        expired: bool = False,
        incoming: int = 0,
        outgoing: int = 0,
    ) -> None:
        assert c.workspace_id
        async with transaction(self.engine) as s:
            await WorkspaceAccess(s).lock_system(c.workspace_id)
            row = await get_row(s, c.workspace_id, c.aggregate_id)
            row.input_tokens = max(row.input_tokens, incoming, 0)
            row.output_tokens = max(row.output_tokens, outgoing, 0)
            if row.status in TERMINAL:
                return
            try:
                await authorize(s, row.requested_by, row.workspace_id, row.id, True)
            except AppException:
                code, result = "ACCESS_REVOKED", None
            job = await jobs.fence(s, c, expired)
            if not job:
                return
            jobs.finish(job, code, retry=False)
            row.status, row.error_code, row.finished_at = (
                ("FAILED" if code else "COMPLETED"),
                code,
                datetime.now(UTC),
            )
            row.result = result
            row.usage_uncertain = bool(code and row.call_attempts)
