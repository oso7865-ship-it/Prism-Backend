from enum import StrEnum


class ErrorKind(StrEnum):
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_INPUT = "INVALID_INPUT"
    UNAVAILABLE = "UNAVAILABLE"


class AppException(Exception):
    def __init__(self, code: str, public_message: str, kind: ErrorKind) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.kind = kind
