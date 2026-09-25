from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LoginStart:
    url: str = field(repr=False)
    binding: str = field(repr=False)


@dataclass(frozen=True)
class SessionTokens:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_at: datetime
