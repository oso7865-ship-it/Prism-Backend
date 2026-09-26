from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1, le=10000)
    pr_number: int | None = Field(default=None, gt=0, le=2147483647)

    @model_validator(mode="after")
    def unambiguous_scope(self) -> "SyncRequest":
        if self.pr_number is not None and self.page != 1:
            raise ValueError("A single PR request cannot specify another page")
        return self


class SyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    fetched_count: int
    next_cursor: str | None
    error_code: str | None
    last_success_at: datetime | None


class PRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    repository_connection_id: UUID
    pr_number: int
    title: str
    author_login: str | None
    state: str
    merge_status: str
    is_draft: bool
    base_sha: str | None
    head_sha: str | None
    github_updated_at: datetime
    synced_at: datetime
