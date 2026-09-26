from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SyncView:
    id: UUID
    status: str
    fetched_count: int
    next_cursor: str | None
    error_code: str | None
    last_success_at: datetime | None


@dataclass(frozen=True)
class PRView:
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
