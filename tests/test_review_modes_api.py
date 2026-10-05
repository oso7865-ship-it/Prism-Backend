import json
from contextlib import asynccontextmanager
from io import StringIO
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.auth.api import CurrentPrincipal
from app.domain.auth.exceptions import SessionExpired
from app.domain.review.models import ReviewRun
from app.domain.review.policy import prepare
from app.domain.review.router import view
from app.domain.user import router as user_router_module
from app.domain.user.dto import UserSnapshot
from app.domain.user.models import User
from app.shared.exception.handlers import register_handlers

USER_ID = uuid4()


class FakeAuth:
    def __init__(self, mode="SENIOR", authenticated=True):
        self.snapshot = UserSnapshot(USER_ID, 1, "tester", "Tester", None, mode)
        self.authenticated = authenticated

    async def require_principal(self):
        if not self.authenticated:
            raise SessionExpired()
        return CurrentPrincipal(USER_ID, self.snapshot)


class FakeUserAPI:
    saved: list[tuple[object, str]] = []

    def __init__(self, session):
        self.session = session

    async def set_review_mode(self, user_id, mode):
        FakeUserAPI.saved.append((user_id, mode))
        return UserSnapshot(user_id, 1, "tester", "Tester", None, mode)


@asynccontextmanager
async def fake_transaction(engine):
    yield object()


def client(monkeypatch, auth=None, engine=object()):
    FakeUserAPI.saved = []
    monkeypatch.setattr(user_router_module, "UserAPI", FakeUserAPI)
    monkeypatch.setattr(user_router_module, "transaction", fake_transaction)
    app = FastAPI()
    register_handlers(app)
    app.include_router(user_router_module.user_router(auth or FakeAuth(), engine))
    return TestClient(app)


def test_profile_response_includes_the_review_mode_default(monkeypatch):
    response = client(monkeypatch).get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["review_mode"] == "SENIOR"


@pytest.mark.parametrize("mode", ["JUNIOR", "SENIOR"])
def test_preferences_update_stores_the_requested_mode_for_the_authenticated_user(monkeypatch, mode):
    response = client(monkeypatch).patch("/api/v1/users/me/preferences", json={"review_mode": mode})
    assert response.status_code == 200
    assert response.json()["review_mode"] == mode
    assert FakeUserAPI.saved == [(USER_ID, mode)]


@pytest.mark.parametrize(
    "body",
    [
        {"review_mode": "MIDDLE"},
        {"review_mode": "junior"},
        {"review_mode": ""},
        {"review_mode": None},
        {"review_mode": 1},
        {},
        {"review_mode": "JUNIOR", "role": "ADMIN"},
    ],
)
def test_preferences_reject_unknown_modes_and_extra_fields(monkeypatch, body):
    response = client(monkeypatch).patch("/api/v1/users/me/preferences", json=body)
    assert response.status_code == 422
    assert FakeUserAPI.saved == []


def test_preferences_require_authentication(monkeypatch):
    response = client(monkeypatch, FakeAuth(authenticated=False)).patch(
        "/api/v1/users/me/preferences", json={"review_mode": "JUNIOR"}
    )
    assert response.status_code == 401
    assert FakeUserAPI.saved == []


def test_preferences_report_unavailable_without_a_database(monkeypatch):
    response = client(monkeypatch, engine=None).patch(
        "/api/v1/users/me/preferences", json={"review_mode": "JUNIOR"}
    )
    assert response.status_code == 503
    assert FakeUserAPI.saved == []


def test_models_default_to_senior_and_constrain_the_mode():
    for table, column, constraint in (
        (User.__table__, "review_mode", "ck_users_review_mode"),
        (ReviewRun.__table__, "mode", "ck_review_mode"),
    ):
        assert str(table.c[column].server_default.arg) == "'SENIOR'"
        assert not table.c[column].nullable
        names = {c.name for c in table.constraints}
        assert constraint in names


def test_migration_0010_is_additive_defaulted_and_the_head(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://offline@127.0.0.1/offline")
    output = StringIO()
    command.upgrade(Config("alembic.ini", output_buffer=output), "0009:0010", sql=True)
    sql = output.getvalue()
    assert "ALTER TABLE users ADD COLUMN review_mode VARCHAR(8) DEFAULT 'SENIOR' NOT NULL" in sql
    assert "ALTER TABLE review_runs ADD COLUMN mode VARCHAR(8) DEFAULT 'SENIOR' NOT NULL" in sql
    assert "CHECK (review_mode IN ('JUNIOR', 'SENIOR'))" in sql
    assert "CHECK (mode IN ('JUNIOR','SENIOR'))" in sql
    assert "FOREIGN KEY" not in sql and "DROP" not in sql
    full = StringIO()
    command.upgrade(Config("alembic.ini", output_buffer=full), "head", sql=True)
    assert "UPDATE alembic_version SET version_num='0010'" in full.getvalue()


def test_prepare_embeds_only_a_valid_server_mode_and_counts_it_in_the_payload():
    change = {"filename": "a.py", "patch": "@@ -1,1 +1,1 @@\n+x = 1"}
    plain = prepare([change], [], [], 1)
    junior = prepare([change], [], [], 1, review_mode="JUNIOR")
    assert "review_mode" not in json.loads(plain.payload)
    assert json.loads(junior.payload)["review_mode"] == "JUNIOR"
    assert len(junior.payload) > len(plain.payload)
    for bad in ("MIDDLE", "junior", "../x"):
        with pytest.raises(ValueError, match="INVALID_REVIEW_MODE"):
            prepare([change], [], [], 1, review_mode=bad)


def test_review_view_exposes_the_run_mode():
    row = ReviewRun(mode="JUNIOR", purpose="CODE")
    assert view(row)["mode"] == "JUNIOR"
