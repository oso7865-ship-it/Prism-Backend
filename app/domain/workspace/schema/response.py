from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    role: str


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    role: str


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    target_github_user_id: int
    role: str
    status: str
    expires_at: datetime


class CreatedInvitationResponse(BaseModel):
    invitation: InvitationResponse
    token: str


class Page[T](BaseModel):
    items: list[T]
    next_cursor: UUID | None = None
