from app.shared.exception.base import AppException, ErrorKind


class LoginRejected(AppException):
    def __init__(self) -> None:
        super().__init__("LOGIN_REJECTED", "로그인을 다시 시작해 주세요.", ErrorKind.UNAUTHORIZED)


class SessionExpired(AppException):
    def __init__(self) -> None:
        super().__init__("SESSION_EXPIRED", "다시 로그인해 주세요.", ErrorKind.UNAUTHORIZED)


class AuthUnavailable(AppException):
    def __init__(self) -> None:
        super().__init__("AUTH_UNAVAILABLE", "로그인 연결을 준비 중입니다.", ErrorKind.UNAVAILABLE)


class ProviderUnavailable(AppException):
    def __init__(self) -> None:
        super().__init__(
            "PROVIDER_UNAVAILABLE",
            "GitHub 연결에 실패했습니다. 다시 시도해 주세요.",
            ErrorKind.UNAVAILABLE,
        )


class OriginRejected(AppException):
    def __init__(self) -> None:
        super().__init__("ORIGIN_REJECTED", "허용되지 않은 요청입니다.", ErrorKind.FORBIDDEN)
