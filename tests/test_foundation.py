import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.shared.config.settings import Settings
from app.shared.observability.health import database_ready


def test_liveness_does_not_claim_database_ready() -> None:
    with TestClient(create_app(Settings(_env_file=None, database_url=None))) as client:
        assert client.get("/health/live").status_code == 200
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready"}
        assert response.headers["cache-control"] == "no-store"


def test_ready_when_dependency_is_available() -> None:
    async def ready() -> bool:
        return True

    with TestClient(create_app(Settings(_env_file=None, database_url=None), ready)) as client:
        assert client.get("/health/ready").status_code == 200


def test_ai_cannot_be_enabled_before_implementation() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ai_enabled=True)


def test_database_secret_is_masked_and_wrong_driver_is_rejected() -> None:
    secret = "canary-password"
    settings = Settings(
        _env_file=None, database_url=f"postgresql+psycopg://user:{secret}@localhost/prism"
    )
    assert secret not in repr(settings)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url=f"mysql://user:{secret}@localhost/prism")
    assert secret not in str(error.value)
    assert asyncio.run(database_ready(None)) is False
