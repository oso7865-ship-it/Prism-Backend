from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class WorkspaceView:
    id: UUID
    name: str
    role: str


@dataclass(frozen=True)
class MemberView:
    user_id: UUID
    role: str


@dataclass(frozen=True)
class InvitationView:
    id: UUID
    target_github_user_id: int
    role: str
    status: str
    expires_at: datetime


@dataclass(frozen=True)
class InvitationCreated:
    invitation: InvitationView
    token: str
