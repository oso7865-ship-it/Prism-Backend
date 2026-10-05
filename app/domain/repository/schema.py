from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_GITHUB_ID = 9223372036854775807


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    github_repository_id: int
    owner_login: str
    repository_name: str
    status: str
    connection_generation: int
    last_sync_success_at: datetime | None


class ConnectStart(BaseModel):
    authorization_url: str


class AppStatus(BaseModel):
    configured: bool
    installation_url: str | None


class CandidateResponse(BaseModel):
    github_repository_id: int
    owner_login: str
    repository_name: str
    is_private: bool
    state: Literal["AVAILABLE", "CONNECTED", "ADMIN_REQUIRED", "OTHER_TEAM"]


class CandidateListResponse(BaseModel):
    items: list[CandidateResponse]
    truncated: bool
    skipped_installations: int
    expires_at: datetime
    installation_url: str | None


class SelectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    github_repository_ids: list[int] = Field(min_length=1, max_length=20)

    @field_validator("github_repository_ids")
    @classmethod
    def valid_ids(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value) or any(not 0 < item <= MAX_GITHUB_ID for item in value):
            raise ValueError("Invalid repository ids")
        return value


class SelectResult(BaseModel):
    github_repository_id: int
    owner_login: str | None
    repository_name: str | None
    status: Literal[
        "CONNECTED", "ALREADY_CONNECTED", "ADMIN_REQUIRED", "NOT_IN_LIST", "CONFLICT", "FAILED"
    ]
    repository_id: UUID | None = None


class SelectResponse(BaseModel):
    results: list[SelectResult]
