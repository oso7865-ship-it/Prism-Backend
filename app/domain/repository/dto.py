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
class CandidateRepository:
    github_repository_id: int
    installation_id: int
    owner_login: str
    repository_name: str
    is_private: bool
    default_branch: str | None
    admin: bool


@dataclass(frozen=True)
class CandidateList:
    items: list[CandidateRepository]
    truncated: bool
    skipped_installations: int


@dataclass(frozen=True)
class CandidateView:
    expires_at: datetime
    truncated: bool
    skipped_installations: int
    items: list[tuple[CandidateRepository, str]]


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
