from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

ISSUER = "prism"
AUDIENCE = "prism-api"
ACCESS_SECONDS = 900


def encode_access(user_id: UUID, key: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_SECONDS),
            "jti": str(uuid4()),
            "type": "access",
        },
        key,
        algorithm="HS256",
    )


def decode_access(token: str, key: str) -> UUID:
    if len(token) > 4096:
        raise ValueError("Invalid access token")
    claims = jwt.decode(
        token,
        key,
        algorithms=["HS256"],
        issuer=ISSUER,
        audience=AUDIENCE,
        options={"require": ["sub", "iss", "aud", "iat", "exp", "jti", "type"]},
    )
    if claims["type"] != "access":
        raise ValueError("Invalid access token")
    return UUID(claims["sub"])
