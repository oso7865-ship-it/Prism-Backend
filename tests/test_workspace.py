from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_auth import KEY
from test_auth import auth_settings as auth_settings

from app.domain.user.models import User
from app.domain.workspace.models import WorkspaceMember
from app.main import create_app
from app.shared.database.event_loop import loop_factory
from app.shared.security.token_codec import encode_access


def users(db):
    with Session(db) as s, s.begin():
        rows = [User(github_user_id=n, login=f"user{n}") for n in range(100, 104)]
        s.add_all(rows)
        s.flush()
        return [(u.id, u.github_user_id) for u in rows]


def test_workspace_permissions_and_invitation(db, auth_settings):
    identities = users(db)
    with TestClient(create_app(auth_settings), backend_options={"loop_factory": loop_factory}) as c:

        def h(i):
            return {"Authorization": "Bearer " + encode_access(identities[i][0], KEY)}

        def call(method, path, i=0, **kw):
            return c.request(method, "/api/v1" + path, headers=h(i), **kw)

        assert c.get("/api/v1/workspaces").status_code == 401
        assert call("POST", "/workspaces", json={"name": "  "}).status_code == 422
        w = call("POST", "/workspaces", json={"name": "Team"}).json()
        wid = w["id"]
        assert call("GET", f"/workspaces/{wid}/members", 1).status_code == 404
        assert call("GET", "/workspaces", 1).json()["items"] == []
        url = f"/workspaces/{wid}"
        result = call("POST", url + "/invitations", json={"target_github_user_id": 101}).json()
        token = result["token"]
        assert token not in call("GET", url + "/invitations").text
        assert call("POST", "/invitations/accept", 2, json={"token": token}).status_code == 403
        assert call("POST", "/invitations/accept", 1, json={"token": token}).status_code == 200
        assert call("POST", "/invitations/accept", 1, json={"token": token}).status_code == 409
        assert (
            call("POST", url + "/invitations", 1, json={"target_github_user_id": 102}).status_code
            == 403
        )
        target = str(identities[1][0])
        assert (
            call("PATCH", url + f"/members/{target}", 1, json={"role": "ADMIN"}).status_code == 403
        )
        assert call("PATCH", url + f"/members/{target}", json={"role": "ADMIN"}).status_code == 200
        assert (
            call(
                "POST",
                url + "/invitations",
                1,
                json={"target_github_user_id": 102, "role": "ADMIN"},
            ).status_code
            == 403
        )
        assert call("DELETE", url + f"/members/{identities[0][0]}").status_code == 409
        assert (
            call("POST", url + "/transfer-ownership", json={"user_id": target}).status_code == 200
        )
        assert (
            call("POST", url + "/transfer-ownership", json={"user_id": target}).status_code == 403
        )
        assert call("DELETE", url + f"/members/{identities[0][0]}", 1).status_code == 204
        assert call("GET", url + "/members").status_code == 404
        assert call("GET", "/workspaces").json()["items"] == []
        with Session(db) as s:
            owners = s.scalars(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == UUID(wid),
                    WorkspaceMember.role == "OWNER",
                    WorkspaceMember.status == "ACTIVE",
                )
            ).all()
            assert len(owners) == 1


def test_concurrent_invitation_acceptance(db, auth_settings):
    identities = users(db)
    with TestClient(create_app(auth_settings), backend_options={"loop_factory": loop_factory}) as c:
        owner = {"Authorization": "Bearer " + encode_access(identities[0][0], KEY)}
        target = {"Authorization": "Bearer " + encode_access(identities[1][0], KEY)}
        wid = c.post("/api/v1/workspaces", headers=owner, json={"name": "Race"}).json()["id"]
        token = c.post(
            f"/api/v1/workspaces/{wid}/invitations",
            headers=owner,
            json={"target_github_user_id": 101},
        ).json()["token"]
        with ThreadPoolExecutor(2) as pool:
            results = list(
                pool.map(
                    lambda _: (
                        c.post(
                            "/api/v1/invitations/accept", headers=target, json={"token": token}
                        ).status_code
                    ),
                    range(2),
                )
            )
        assert sorted(results) == [200, 409]


def test_concurrent_owner_transfer(db, auth_settings):
    u = users(db)
    with TestClient(create_app(auth_settings), backend_options={"loop_factory": loop_factory}) as c:
        h = {"Authorization": "Bearer " + encode_access(u[0][0], KEY)}
        wid = c.post("/api/v1/workspaces", headers=h, json={"name": "Owners"}).json()["id"]
        for uid, gid in u[1:3]:
            token = c.post(
                f"/api/v1/workspaces/{wid}/invitations",
                headers=h,
                json={"target_github_user_id": gid},
            ).json()["token"]
            assert (
                c.post(
                    "/api/v1/invitations/accept",
                    headers={"Authorization": "Bearer " + encode_access(uid, KEY)},
                    json={"token": token},
                ).status_code
                == 200
            )
        with ThreadPoolExecutor(2) as pool:
            statuses = list(
                pool.map(
                    lambda target: (
                        c.post(
                            f"/api/v1/workspaces/{wid}/transfer-ownership",
                            headers=h,
                            json={"user_id": str(target[0])},
                        ).status_code
                    ),
                    u[1:3],
                )
            )
        assert sorted(statuses) == [200, 403]
        with Session(db) as s:
            assert (
                len(
                    s.scalars(
                        select(WorkspaceMember).where(
                            WorkspaceMember.workspace_id == UUID(wid),
                            WorkspaceMember.role == "OWNER",
                            WorkspaceMember.status == "ACTIVE",
                        )
                    ).all()
                )
                == 1
            )
