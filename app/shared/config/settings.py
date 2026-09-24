from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: Literal["development", "test"] = "development"
    database_url: SecretStr | None = None
    ai_enabled: bool = False
    job_runner_mode: Literal["disabled"] = "disabled"

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
        return self
