from app.domain.workspace.role import Role


def allowed(role: str, permission: str) -> bool:
    grants = {
        "read": {Role.OWNER, Role.ADMIN, Role.MEMBER},
        "sync": {Role.OWNER, Role.ADMIN, Role.MEMBER},
        "manage": {Role.OWNER, Role.ADMIN},
        "owner": {Role.OWNER},
    }
    return role in grants.get(permission, set())
