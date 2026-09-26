import base64
import hashlib
import json
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.shared.config.settings import Settings
from app.shared.exception.base import AppException, ErrorKind


class GitHubFailure(AppException):
    def __init__(self, code: str = "GITHUB_UNAVAILABLE", retry_after: int | None = None) -> None:
        super().__init__(code, "GitHub 연결 또는 권한을 확인해 주세요.", ErrorKind.UNAVAILABLE)
        self.retry_after = retry_after


class GitHubClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client

    def ready(self) -> None:
        if not self.settings.github_app_ready:
            raise GitHubFailure("GITHUB_APP_NOT_CONFIGURED")

    def app_jwt(self) -> str:
        self.ready()
        assert self.settings.github_app_private_key
        try:
            return jwt.encode(
                {
                    "iat": int(time.time()) - 60,
                    "exp": int(time.time()) + 480,
                    "iss": str(self.settings.github_app_id),
                },
                self.settings.github_app_private_key.get_secret_value().replace("\\n", "\n"),
                algorithm="RS256",
            )
        except (ValueError, TypeError, jwt.PyJWTError):
            raise GitHubFailure("GITHUB_APP_CONFIG_INVALID") from None

    def authorization_url(self, state: str, binding: str) -> str:
        self.ready()
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(binding.encode()).digest()).decode().rstrip("=")
        )
        return "https://github.com/login/oauth/authorize?" + urlencode(
            {
                "client_id": self.settings.github_app_client_id,
                "redirect_uri": self.settings.app_callback_url,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )

    async def request(
        self,
        method: str,
        path: str,
        token: str | None = None,
        *,
        body: dict[str, object] | None = None,
        oauth: bool = False,
        etag: str | None = None,
        cache: bool = False,
    ) -> Any:
        base = "https://github.com" if oauth else "https://api.github.com"
        if not path.startswith("/") or path.startswith("//"):
            raise GitHubFailure()
        headers = {
            "Accept": "application/json" if oauth else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if etag:
            headers["If-None-Match"] = etag
        if token:
            headers["Authorization"] = "Bearer " + token
        try:
            async with self.client.stream(
                method, base + path, headers=headers, json=body, timeout=10, follow_redirects=False
            ) as response:
                if response.status_code == 304 and cache:
                    if not etag:
                        raise GitHubFailure("GITHUB_INVALID_RESPONSE")
                    return None, etag
                if response.status_code in (403, 429) and (
                    response.headers.get("retry-after")
                    or response.headers.get("x-ratelimit-remaining") == "0"
                ):
                    delay = 60
                    try:
                        delay = max(1, min(86400, int(response.headers.get("retry-after", "60"))))
                    except ValueError:
                        pass
                    try:
                        reset = int(response.headers.get("x-ratelimit-reset", "0"))
                        delay = max(delay, min(86400, reset - int(time.time()) + 1))
                    except ValueError:
                        pass
                    raise GitHubFailure("GITHUB_RATE_LIMIT", delay)
                if response.status_code in (401, 403, 404):
                    raise GitHubFailure("GITHUB_ACCESS_UNAVAILABLE")
                if response.status_code >= 500:
                    raise GitHubFailure()
                if not 200 <= response.status_code < 300:
                    raise GitHubFailure("GITHUB_INVALID_RESPONSE")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 2 * 1024 * 1024:
                        raise GitHubFailure("GITHUB_RESPONSE_TOO_LARGE")
                data = json.loads(content)
                tag = response.headers.get("etag")
                if tag and len(tag) > 512:
                    tag = None
                return (data, tag) if cache else data
        except (httpx.HTTPError, ValueError):
            raise GitHubFailure() from None

    async def user_token(self, code: str, binding: str) -> str:
        self.ready()
        assert self.settings.github_app_client_secret
        data = await self.request(
            "POST",
            "/login/oauth/access_token",
            body={
                "client_id": self.settings.github_app_client_id,
                "client_secret": self.settings.github_app_client_secret.get_secret_value(),
                "code": code,
                "redirect_uri": self.settings.app_callback_url,
                "code_verifier": binding,
            },
            oauth=True,
        )
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("access_token"), str)
            or not 1 <= len(data["access_token"]) <= 4096
        ):
            raise GitHubFailure()
        return str(data["access_token"])

    async def installation_token(self, installation: int, repository: int) -> str:
        data = await self.request(
            "POST",
            f"/app/installations/{installation}/access_tokens",
            self.app_jwt(),
            body={
                "repository_ids": [repository],
                "permissions": {"contents": "read", "pull_requests": "read", "issues": "read"},
            },
        )
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("token"), str)
            or not 1 <= len(data["token"]) <= 4096
        ):
            raise GitHubFailure()
        return str(data["token"])
