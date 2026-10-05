from pydantic import BaseModel, Field, ValidationError

from app.domain.repository.dto import CandidateList, CandidateRepository
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


MAX_INSTALLATIONS = 20
MAX_CANDIDATES = 300
REQUIRED_PERMISSIONS = ("contents", "pull_requests", "issues")


async def collect(
    github: GitHubClient, code: str, binding: str, expected_user: int
) -> CandidateList:
    """List every repository the signed-in user can connect through this GitHub App.

    The user token lives only inside this call. Nothing is connected here.
    """
    token = await github.user_token(code, binding)
    user = await github.request("GET", "/user", token)
    if not isinstance(user, dict) or type(user.get("id")) is not int or user["id"] != expected_user:
        raise GitHubFailure("GITHUB_USER_MISMATCH")
    data = await github.request("GET", "/user/installations?per_page=100", token)
    if not isinstance(data, dict) or not isinstance(data.get("installations"), list):
        raise GitHubFailure("GITHUB_INVALID_RESPONSE")
    usable: list[Installation] = []
    skipped = 0
    for raw in data["installations"]:
        try:
            installation = Installation.model_validate(raw)
        except ValidationError:
            skipped += 1
            continue
        if (
            installation.app_id != github.settings.github_app_id
            or installation.suspended_at
            or any(
                installation.permissions.get(p) not in {"read", "write"}
                for p in REQUIRED_PERMISSIONS
            )
        ):
            skipped += 1
        else:
            usable.append(installation)
    items: dict[int, CandidateRepository] = {}
    truncated = len(usable) > MAX_INSTALLATIONS
    for installation in usable[:MAX_INSTALLATIONS]:
        for page in range(1, 4):
            data = await github.request(
                "GET",
                f"/user/installations/{installation.id}/repositories?per_page=100&page={page}",
                token,
            )
            if not isinstance(data, dict) or not isinstance(data.get("repositories"), list):
                raise GitHubFailure("GITHUB_INVALID_RESPONSE")
            for raw in data["repositories"]:
                try:
                    repo = RemoteRepository.model_validate(raw)
                except ValidationError:
                    continue  # one unusual entry must not hide the others
                if repo.id in items:
                    continue
                if len(items) >= MAX_CANDIDATES:
                    truncated = True
                    continue
                items[repo.id] = CandidateRepository(
                    repo.id,
                    installation.id,
                    repo.owner.login,
                    repo.name,
                    repo.private,
                    repo.default_branch,
                    repo.permissions.admin,
                )
            if len(data["repositories"]) < 100:
                break
        else:
            truncated = True
    return CandidateList(list(items.values()), truncated, skipped)
