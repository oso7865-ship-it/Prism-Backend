from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConnectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,99}/[A-Za-z0-9_.-]{1,100}$")

    @field_validator("full_name")
    @classmethod
    def safe_name(cls, value: str) -> str:
        if value.split("/")[1] in {".", ".."}:
            raise ValueError("Invalid repository name")
        return value


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
