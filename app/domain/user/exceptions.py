from app.shared.exception.base import AppException, ErrorKind


class UserUnavailable(AppException):
    def __init__(self) -> None:
        super().__init__("USER_UNAVAILABLE", "사용할 수 없는 계정입니다.", ErrorKind.UNAUTHORIZED)
