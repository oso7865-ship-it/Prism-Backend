from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    github_user_id: int
    login: str
    display_name: str | None
    avatar_url: str | None
