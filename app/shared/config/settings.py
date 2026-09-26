import ipaddress
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test", "production"] = "development"
    database_url: SecretStr | None = None
    ai_enabled: bool = False
    deepseek_api_key: SecretStr | None = None
    deepseek_model: Literal["deepseek-flash", "deepseek-v4-pro", "deepseek-chat"] = "deepseek-flash"
    ai_daily_limit: int = Field(default=5, ge=1, le=5)
    job_runner_mode: Literal["disabled"] = "disabled"
    auth_enabled: bool = False
    github_app_id: int | None = Field(default=None, gt=0)
    github_app_slug: str | None = None
    github_app_client_id: str | None = None
    github_app_client_secret: SecretStr | None = None
    github_app_private_key: SecretStr | None = None
    github_webhook_secret: SecretStr | None = None
    sync_runner_enabled: bool = False
    analysis_runner_enabled: bool = False
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: SecretStr | None = None
    jwt_signing_key: SecretStr | None = None
    public_app_origin: str = "http://localhost:5173"
    public_api_origin: str = "http://localhost:8000"

    @field_validator("public_app_origin", "public_api_origin")
    @classmethod
    def bare_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or any(c.isspace() for c in value)
            or "\\" in value
            or "?" in value
            or "#" in value
        ):
            raise ValueError("A bare HTTP(S) origin is required")
        try:
            parsed.port
        except ValueError:
            raise ValueError("Invalid origin port") from None
        return value

    @property
    def secure_cookies(self) -> bool:
        return self.app_env == "production"

    @property
    def github_app_ready(self) -> bool:
        return bool(
            self.github_app_id
            and self.github_app_slug
            and self.github_app_client_id
            and self.github_app_client_secret
            and self.github_app_private_key
        )

    @property
    def app_callback_url(self) -> str:
        return self.public_api_origin + "/api/v1/github-app/callback"

    @field_validator("github_app_slug")
    @classmethod
    def valid_slug(cls, value: str | None) -> str | None:
        import re

        if value is not None and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", value):
            raise ValueError("Invalid GitHub App slug")
        return value

    @property
    def oauth_callback_url(self) -> str:
        return self.public_api_origin + "/api/v1/auth/github/callback"

    @property
    def auth_ready(self) -> bool:
        return bool(
            self.auth_enabled
            and self.database_url
            and self.github_oauth_client_id
            and self.github_oauth_client_secret
            and self.jwt_signing_key
        )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            try:
                url = make_url(value.get_secret_value())
                if url.drivername != "postgresql+psycopg" or not url.database:
                    raise ValueError
            except Exception:
                raise ValueError("DATABASE_URL must be a PostgreSQL psycopg URL") from None
        return value

    @model_validator(mode="after")
    def validate_runtime(self) -> "Settings":
        if self.ai_enabled and not (
            self.deepseek_api_key
            and self.database_url
            and self.auth_ready
            and self.github_app_ready
        ):
            raise ValueError(
                "AI requires DeepSeek key, database, authentication and GitHub App settings"
            )
        if self.jwt_signing_key and len(self.jwt_signing_key.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SIGNING_KEY must contain at least 32 bytes")
        origins = [urlsplit(self.public_app_origin), urlsplit(self.public_api_origin)]
        if self.app_env == "production":
            for origin in origins:
                host = origin.hostname or ""
                if origin.scheme != "https" or origin.port not in (None, 443):
                    raise ValueError("Production origins require HTTPS on port 443")
                if origin.geturl() != f"https://{host}":
                    raise ValueError("Production origins require lowercase hostnames without ports")
                if "." not in host or host.endswith((".localhost", ".local", ".invalid")):
                    raise ValueError("Production origins require a public DNS hostname")
                if len(host) > 253 or any(
                    not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                    for label in host.split(".")
                ):
                    raise ValueError("Invalid production hostname")
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    pass
                else:
                    raise ValueError("Production origins must use DNS hostnames")
            if self.public_app_origin != self.public_api_origin:
                raise ValueError("Production OAuth/API must use the exact frontend proxy origin")
            if not self.auth_ready:
                raise ValueError(
                    "Production requires database and complete authentication settings"
                )
            assert self.database_url
            if make_url(self.database_url.get_secret_value()).query.get("sslmode") != "verify-full":
                raise ValueError("Production database requires sslmode=verify-full")
            if self.sync_runner_enabled or self.analysis_runner_enabled:
                if not self.github_app_ready:
                    raise ValueError("Production runners require complete GitHub App settings")
            if self.github_app_ready and (
                not self.github_webhook_secret
                or len(self.github_webhook_secret.get_secret_value().encode()) < 32
            ):
                raise ValueError(
                    "Production GitHub App requires a webhook secret of at least 32 bytes"
                )
        else:
            if any(
                o.scheme != "http" or o.hostname not in {"localhost", "127.0.0.1"} for o in origins
            ):
                raise ValueError("Development/test origins must use local HTTP")
            if origins[0].hostname != origins[1].hostname:
                raise ValueError("Local app and API origins must use the same cookie hostname")
        return self
