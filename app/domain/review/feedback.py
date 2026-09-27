from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.domain.review.models import ReviewFeedback, ReviewRun
from app.domain.review.policy import SECRET, issue_key
from app.domain.review.service import authorize, error
from app.shared.database.engine import transaction
from app.shared.exception.base import ErrorKind


def entries(row: ReviewRun) -> list[dict[str, object]]:
    result = row.result or {}
    issues = cast(list[dict[str, object]], result.get("issues", []))
    questions = cast(list[dict[str, object]], result.get("questions", []))
    return issues + questions


async def list_feedback(
    engine: AsyncEngine, uid: UUID, wid: UUID, rid: UUID
) -> list[ReviewFeedback]:
    async with transaction(engine) as s:
        await authorize(s, uid, wid, rid)
        return list(
            (
                await s.scalars(
                    select(ReviewFeedback).where(
                        ReviewFeedback.workspace_id == wid,
                        ReviewFeedback.review_id == rid,
                        ReviewFeedback.user_id == uid,
                    )
                )
            ).all()
        )


async def save_feedback(
    engine: AsyncEngine,
    uid: UUID,
    wid: UUID,
    rid: UUID,
    key: str,
    state: str,
    note: str,
) -> ReviewFeedback:
    if (
        SECRET.search(note)
        or len(note) > 500
        or state not in ("OPEN", "ACKNOWLEDGED", "PLANNED", "INTENDED", "FALSE_POSITIVE")
    ):
        raise error("INVALID_FEEDBACK", ErrorKind.INVALID_INPUT)
    async with transaction(engine) as s:
        # Review row lock serializes first insert and concurrent updates for this run.
        row = await authorize(s, uid, wid, rid)
        if row.status != "COMPLETED" or key not in {issue_key(i) for i in entries(row)}:
            raise error("FINDING_NOT_FOUND", ErrorKind.NOT_FOUND)
        item = await s.scalar(
            select(ReviewFeedback).where(
                ReviewFeedback.workspace_id == wid,
                ReviewFeedback.review_id == rid,
                ReviewFeedback.user_id == uid,
                ReviewFeedback.issue_key == key,
            )
        )
        if item is None:
            item = ReviewFeedback(
                workspace_id=wid,
                review_id=rid,
                user_id=uid,
                issue_key=key,
                state=state,
                note=note.strip(),
            )
            s.add(item)
        else:
            item.state, item.note = state, note.strip()
        await s.flush()
        await s.refresh(item)
        return item


async def prior_feedback(s: AsyncSession, row: ReviewRun) -> list[dict[str, str]]:
    records = (
        await s.execute(
            select(ReviewFeedback, ReviewRun)
            .join(ReviewRun, ReviewRun.id == ReviewFeedback.review_id)
            .where(
                ReviewFeedback.workspace_id == row.workspace_id,
                ReviewFeedback.user_id == row.requested_by,
                ReviewRun.pr_id == row.pr_id,
                ReviewRun.id != row.id,
                ReviewFeedback.state != "OPEN",
            )
            .order_by(ReviewFeedback.updated_at.desc())
            .limit(5)
        )
    ).all()
    result = []
    for feedback, previous in records:
        issue = next((i for i in entries(previous) if issue_key(i) == feedback.issue_key), None)
        if issue:
            result.append(
                {"title": str(issue["title"]), "state": feedback.state, "note": feedback.note}
            )
    return result
