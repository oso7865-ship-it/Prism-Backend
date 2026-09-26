from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.shared.github.client import GitHubClient, GitHubFailure


class Author(BaseModel):
    id: int = Field(gt=0, strict=True)
    login: str = Field(max_length=255)


class Ref(BaseModel):
    ref: str | None = Field(default=None, max_length=1024)
    sha: str | None = Field(default=None, pattern=r"^([0-9a-f]{40}|[0-9a-f]{64})$")


class RemotePR(BaseModel):
    id: int = Field(gt=0, le=9223372036854775807, strict=True)
    number: int = Field(gt=0, le=2147483647, strict=True)
    title: str = Field(max_length=4096)
    user: Author | None = None
    state: Literal["open", "closed"]
    draft: bool
    base: Ref
    head: Ref
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    merged: bool | None = None
    changed_files: int | None = Field(default=None, ge=0)
    commits: int | None = Field(default=None, ge=0)


async def fetch(
    g: GitHubClient,
    installation: int,
    gid: int,
    owner: str,
    name: str,
    page: int,
    number: int | None,
    etag: str | None = None,
) -> tuple[list[RemotePR], str | None, bool]:
    token = await g.installation_token(installation, gid)
    path = f"/repos/{owner}/{name}/pulls"
    path += (
        f"/{number}"
        if number
        else f"?state=all&sort=updated&direction=desc&per_page=30&page={page}"
    )
    data, new_etag = await g.request("GET", path, token, etag=etag, cache=True)
    if data is None:
        return [], new_etag, True
    if number:
        data = [data]
    if not isinstance(data, list) or len(data) > 30:
        raise GitHubFailure("GITHUB_INVALID_RESPONSE")
    try:
        rows = [RemotePR.model_validate(item) for item in data]
        if any(p.updated_at.tzinfo is None or p.created_at.tzinfo is None for p in rows):
            raise GitHubFailure("GITHUB_INVALID_RESPONSE")
        return rows, new_etag, False
    except ValidationError:
        raise GitHubFailure("GITHUB_INVALID_RESPONSE") from None
