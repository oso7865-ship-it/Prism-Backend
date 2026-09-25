from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test"] = "development"
    database_url: SecretStr | None = None
    ai_enabled: bool = False
    job_runner_mode: Literal["disabled"] = "disabled"
    auth_enabled: bool = False
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: SecretStr | None = None
    jwt_signing_key: SecretStr | None = None
    public_app_origin: str = "http://localhost:5173"
    public_api_origin: str = "http://localhost:8000"

    @field_validator("public_app_origin", "public_api_origin")
    @classmethod
    def local_origin_only(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"localhost", "127.0.0.1"}
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Only bare local HTTP origins are supported in development")
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
    def disable_unimplemented_integrations(self) -> "Settings":
        if self.ai_enabled:
            raise ValueError("AI integration is not implemented")
        if self.jwt_signing_key and len(self.jwt_signing_key.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SIGNING_KEY must contain at least 32 bytes")
        if urlsplit(self.public_app_origin).hostname != urlsplit(self.public_api_origin).hostname:
            raise ValueError("Local app and API origins must use the same cookie hostname")
        return self
