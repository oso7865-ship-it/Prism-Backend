import asyncio
import base64
import hashlib
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from app.domain.auth.exceptions import ProviderUnavailable
from app.domain.user.api import GitHubIdentity
from app.shared.config.settings import Settings


class TokenPayload(BaseModel):
    access_token: SecretStr = Field(min_length=1, max_length=4096)
    token_type: str


class ProfilePayload(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int = Field(gt=0, le=9223372036854775807)
    login: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2048)


class GitHubOAuth:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    def authorization_url(self, state: str, verifier: str) -> str:
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        return "https://github.com/login/oauth/authorize?" + urlencode(
            {
                "client_id": self.settings.github_oauth_client_id,
                "redirect_uri": self.settings.oauth_callback_url,
                "scope": "read:user",
                "state": state,
                "code_challenge": challenge.decode().rstrip("="),
                "code_challenge_method": "S256",
            }
        )

    async def _body(
        self, method: str, url: str, *, data: dict[str, str] | None = None, token: str | None = None
    ) -> bytes:
        headers = {"Accept": "application/json", "User-Agent": "PRism-local"}
        if token:
            headers["Authorization"] = "Bearer " + token
        async with (
            asyncio.timeout(10),
            self.client.stream(
                method,
                url,
                data=data,
                headers=headers,
                follow_redirects=False,
                timeout=10,
            ) as response,
        ):
            if response.status_code != 200:
                raise ProviderUnavailable()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 32768:
                    raise ProviderUnavailable()
            return bytes(body)

    async def identity(self, code: str, verifier: str) -> GitHubIdentity:
        secret = self.settings.github_oauth_client_secret
        assert secret is not None
        try:
            token = TokenPayload.model_validate_json(
                await self._body(
                    "POST",
                    "https://github.com/login/oauth/access_token",
                    data={
                        "client_id": self.settings.github_oauth_client_id or "",
                        "client_secret": secret.get_secret_value(),
                        "code": code,
                        "redirect_uri": self.settings.oauth_callback_url,
                        "code_verifier": verifier,
                    },
                )
            )
            if token.token_type.lower() != "bearer":
                raise ProviderUnavailable()
            profile = ProfilePayload.model_validate_json(
                await self._body(
                    "GET",
                    "https://api.github.com/user",
                    token=token.access_token.get_secret_value(),
                )
            )
            return GitHubIdentity(profile.id, profile.login, profile.name, profile.avatar_url)
        except (httpx.HTTPError, TimeoutError, ValidationError):
            # No provider response or exception repr leaves this boundary.
            raise ProviderUnavailable() from None
