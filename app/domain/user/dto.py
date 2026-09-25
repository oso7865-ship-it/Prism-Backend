from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GitHubIdentity:
    github_user_id: int
    login: str
    display_name: str | None
    avatar_url: str | None


@dataclass(frozen=True)
class UserSnapshot:
    id: UUID
    github_user_id: int
    login: str
    display_name: str | None
    avatar_url: str | None
