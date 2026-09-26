from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateWorkspace(RequestModel):
    name: str = Field(min_length=1, max_length=100)


class Invite(RequestModel):
    target_github_user_id: int = Field(gt=0, le=9223372036854775807, strict=True)
    role: Literal["MEMBER", "ADMIN"] = "MEMBER"


class Accept(RequestModel):
    token: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")


class ChangeRole(RequestModel):
    role: Literal["MEMBER", "ADMIN"]


class Transfer(RequestModel):
    user_id: UUID
