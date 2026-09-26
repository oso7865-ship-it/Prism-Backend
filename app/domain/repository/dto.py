from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class VerifiedRepository:
    github_repository_id: int
    installation_id: int
    owner_login: str
    repository_name: str
    is_private: bool
    default_branch: str | None


@dataclass(frozen=True)
class RepositorySnapshot:
    id: UUID
    workspace_id: UUID
    github_repository_id: int
    installation_id: int
    owner_login: str
    repository_name: str
    status: str
    connection_generation: int
    last_sync_success_at: datetime | None
