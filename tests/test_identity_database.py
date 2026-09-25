"""Exercise the frozen migration against isolated schemas in a dedicated PostgreSQL DB."""

import ast
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from uvicorn import Config as UvicornConfig

from app.domain.auth.models import LoginAttempt, RefreshSession
from app.domain.user.models import User
from app.domain.workspace.models import Invitation, Workspace, WorkspaceMember
from app.shared.database.base import Base

TABLES = {
    "users",
    "workspaces",
    "workspace_members",
    "invitations",
    "login_attempts",
    "refresh_sessions",
}
MODELS = {
    model.__tablename__: model
    for model in (User, Workspace, WorkspaceMember, Invitation, LoginAttempt, RefreshSession)
}


def test_metadata_and_dependency_boundary():
    assert set(Base.metadata.tables) == TABLES
    assert not any(table.foreign_keys for table in Base.metadata.tables.values())
    for path in Path("app/shared").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(name.startswith("app.domain") for name in names), path


def test_offline_migration_and_windows_loop(monkeypatch):
    # Offline SQL generation must work in a fresh checkout without a local .env or DB.
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://offline@127.0.0.1/offline")
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    command.upgrade(config, "head", sql=True)
    sql = output.getvalue()
    for table in TABLES:
        assert f"CREATE TABLE {table}" in sql
    assert "FOREIGN KEY" not in sql
    factory = UvicornConfig(
        "app.main:create_app", factory=True, loop="app.shared.database.event_loop:loop_factory"
    ).get_loop_factory()
    loop = factory()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def row(table):
    now = datetime.now(UTC)
    common = {"id": uuid4(), "created_at": now}
    fields = {
        "users": {"github_user_id": 123, "login": "tester"},
        "workspaces": {"name": "Test", "created_by": uuid4()},
        "workspace_members": {"workspace_id": uuid4(), "user_id": uuid4(), "role": "MEMBER"},
        "login_attempts": {
            "purpose": "OAUTH_LOGIN",
            "state_hash": uuid4().hex * 2,
            "browser_binding_hash": "b" * 64,
            "return_path": "/",
            "expires_at": now + timedelta(minutes=10),
        },
        "refresh_sessions": {
            "user_id": uuid4(),
            "family_id": uuid4(),
            "token_hash": uuid4().hex * 2,
            "expires_at": now + timedelta(days=1),
        },
        "invitations": {
            "workspace_id": uuid4(),
            "target_github_user_id": 456,
            "invited_by": uuid4(),
            "token_hash": uuid4().hex * 2,
            "expires_at": now + timedelta(days=1),
        },
    }
    return common | fields[table]


@pytest.mark.integration
def test_catalog_and_orm_roundtrip(db):
    catalog = inspect(db)
    assert set(catalog.get_table_names()) == TABLES
    with Session(db) as session:
        for table, model in MODELS.items():
            assert not catalog.get_foreign_keys(table)
            assert catalog.get_pk_constraint(table)["constrained_columns"] == ["id"]
            assert catalog.get_check_constraints(table)
            values = row(table)
            values.pop("id")
            obj = model(**values)
            session.add(obj)
            session.flush()
            assert isinstance(obj.id, UUID) and obj.created_at.tzinfo is not None
        session.commit()
    with Session(db) as session:
        assert session.scalars(select(User)).one().status == "ACTIVE"
        invitation = session.scalars(select(Invitation)).one()
        assert invitation.status == "PENDING" and invitation.role == "MEMBER"
    for table, index in [
        ("workspace_members", "uq_workspace_members_active_owner"),
        ("invitations", "uq_invitations_pending_target"),
        ("refresh_sessions", "uq_refresh_sessions_replaced_by_id"),
    ]:
        entry = next(item for item in catalog.get_indexes(table) if item["name"] == index)
        assert entry["unique"] and entry["dialect_options"]["postgresql_where"]


@pytest.mark.integration
@pytest.mark.parametrize(
    "table,patch,constraint",
    [
        ("users", {"github_user_id": 0}, "ck_users_github_user_id_positive"),
        ("users", {"status": "DELETED"}, "ck_users_status"),
        ("workspaces", {"name": "  "}, "ck_workspaces_name_nonblank"),
        ("login_attempts", {"state_hash": "bad"}, "ck_login_attempts_state_hash"),
        (
            "login_attempts",
            {"browser_binding_hash": "G" * 64},
            "ck_login_attempts_browser_binding_hash",
        ),
        ("login_attempts", {"purpose": "GITHUB_INSTALL"}, "ck_login_attempts_binding"),
        (
            "login_attempts",
            {"expires_at": datetime(2000, 1, 1, tzinfo=UTC)},
            "ck_login_attempts_expiry",
        ),
        (
            "refresh_sessions",
            {"rotated_at": datetime.now(UTC)},
            "ck_refresh_sessions_rotation_pair",
        ),
        ("refresh_sessions", {"revoke_reason": "logout"}, "ck_refresh_sessions_revocation_pair"),
        ("workspace_members", {"role": "SUPERUSER"}, "ck_workspace_members_role"),
        ("workspace_members", {"status": "LEFT"}, "ck_workspace_members_ended_at"),
        ("invitations", {"role": "OWNER"}, "ck_invitations_role"),
        ("invitations", {"status": "ACCEPTED"}, "ck_invitations_acceptance"),
        ("invitations", {"status": "REVOKED"}, "ck_invitations_revocation"),
    ],
)
def test_invalid_rows_rejected(db, table, patch, constraint):
    with pytest.raises(IntegrityError) as caught, db.begin() as connection:
        connection.execute(Base.metadata.tables[table].insert().values(row(table) | patch))
    assert caught.value.orig.diag.constraint_name == constraint


@pytest.mark.integration
def test_not_null_and_unique_membership(db):
    with pytest.raises(IntegrityError) as caught, db.begin() as connection:
        connection.execute(User.__table__.insert().values(row("users") | {"login": None}))
    assert caught.value.orig.sqlstate == "23502"
    member = row("workspace_members")
    with db.begin() as connection:
        connection.execute(WorkspaceMember.__table__.insert().values(member))
    with pytest.raises(IntegrityError) as caught, db.begin() as connection:
        connection.execute(WorkspaceMember.__table__.insert().values(member | {"id": uuid4()}))
    assert caught.value.orig.diag.constraint_name == "uq_workspace_members_workspace_user"


@pytest.mark.integration
@pytest.mark.parametrize(
    "table,constraint",
    [
        ("users", "uq_users_github_user_id"),
        ("workspace_members", "uq_workspace_members_active_owner"),
        ("invitations", "uq_invitations_pending_target"),
    ],
)
def test_concurrent_unique_writes(db, table, constraint):
    first = row(table)
    second = row(table)
    if table == "workspace_members":
        first["role"] = second["role"] = "OWNER"
        second["workspace_id"] = first["workspace_id"]
    elif table == "invitations":
        second["workspace_id"] = first["workspace_id"]
    barrier = Barrier(2)

    def insert(values):
        try:
            with db.begin() as connection:
                barrier.wait(timeout=10)
                connection.execute(Base.metadata.tables[table].insert().values(values))
            return "committed"
        except IntegrityError as error:
            return error.orig.diag.constraint_name

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(insert, [first, second]))
    assert sorted(results) == sorted(["committed", constraint])


@pytest.mark.integration
def test_owner_transfer_failure_rolls_back_entire_transaction(db):
    owner = row("workspace_members") | {"role": "OWNER"}
    with db.begin() as connection:
        connection.execute(WorkspaceMember.__table__.insert().values(owner))
    with pytest.raises(IntegrityError), db.begin() as connection:
        connection.execute(
            update(WorkspaceMember).where(WorkspaceMember.id == owner["id"]).values(role="MEMBER")
        )
        connection.execute(User.__table__.insert().values(row("users")))
        connection.execute(
            WorkspaceMember.__table__.insert().values(
                row("workspace_members") | {"role": "INVALID"}
            )
        )
    with Session(db) as session:
        assert session.get(WorkspaceMember, owner["id"]).role == "OWNER"
        assert session.scalars(select(User)).all() == []


@pytest.mark.integration
def test_partial_uniqueness_releases_after_end(db):
    invitation = row("invitations")
    with db.begin() as connection:
        connection.execute(Invitation.__table__.insert().values(invitation))
        connection.execute(
            update(Invitation).where(Invitation.id == invitation["id"]).values(status="EXPIRED")
        )
        connection.execute(
            Invitation.__table__.insert().values(
                invitation | {"id": uuid4(), "token_hash": "f" * 64}
            )
        )
    with Session(db) as session:
        assert len(session.scalars(select(Invitation)).all()) == 2
