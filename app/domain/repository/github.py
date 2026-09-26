from pydantic import BaseModel, Field, ValidationError

from app.domain.repository.dto import VerifiedRepository
from app.shared.github.client import GitHubClient, GitHubFailure


class Owner(BaseModel):
    login: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,99}$")


class Permissions(BaseModel):
    admin: bool = Field(default=False, strict=True)


class RemoteRepository(BaseModel):
    id: int = Field(gt=0, le=9223372036854775807, strict=True)
    name: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,100}$")
    owner: Owner
    private: bool
    default_branch: str | None = Field(default=None, max_length=1024)
    permissions: Permissions = Field(default_factory=Permissions)


class Installation(BaseModel):
    id: int = Field(gt=0, le=9223372036854775807, strict=True)
    app_id: int
    suspended_at: str | None = None
    permissions: dict[str, str]


async def verify(
    github: GitHubClient, code: str, binding: str, target: str, expected_user: int
) -> VerifiedRepository:
    try:
        token = await github.user_token(code, binding)
        user = await github.request("GET", "/user", token)
        if (
            not isinstance(user, dict)
            or type(user.get("id")) is not int
            or user["id"] != expected_user
        ):
            raise GitHubFailure("GITHUB_USER_MISMATCH")
        repo = RemoteRepository.model_validate(
            await github.request("GET", "/repos/" + target, token)
        )
        if not repo.permissions.admin:
            raise GitHubFailure("GITHUB_ADMIN_REQUIRED")
        installation = Installation.model_validate(
            await github.request("GET", "/repos/" + target + "/installation", github.app_jwt())
        )
        if installation.app_id != github.settings.github_app_id or installation.suspended_at:
            raise GitHubFailure("GITHUB_ACCESS_UNAVAILABLE")
        if any(
            installation.permissions.get(p) not in {"read", "write"}
            for p in ("contents", "pull_requests", "issues")
        ):
            raise GitHubFailure("GITHUB_PERMISSIONS_REQUIRED")
        found = False
        for page in range(1, 101):
            data = await github.request(
                "GET",
                f"/user/installations/{installation.id}/repositories?per_page=100&page={page}",
                token,
            )
            if not isinstance(data, dict) or not isinstance(data.get("repositories"), list):
                raise GitHubFailure()
            repos = [RemoteRepository.model_validate(item) for item in data["repositories"]]
            if any(item.id == repo.id for item in repos):
                found = True
                break
            if len(repos) < 100:
                break
        if not found:
            raise GitHubFailure("GITHUB_REPOSITORY_NOT_GRANTED")
        return VerifiedRepository(
            repo.id, installation.id, repo.owner.login, repo.name, repo.private, repo.default_branch
        )
    except ValidationError:
        raise GitHubFailure("GITHUB_INVALID_RESPONSE") from None
