from app.shared.exception.base import AppException, ErrorKind


class WorkspaceMissing(AppException):
    def __init__(self) -> None:
        super().__init__(
            "WORKSPACE_NOT_FOUND", "팀 또는 리소스를 찾을 수 없습니다.", ErrorKind.NOT_FOUND
        )


class PermissionDenied(AppException):
    def __init__(self) -> None:
        super().__init__(
            "PERMISSION_DENIED", "이 작업을 수행할 권한이 없습니다.", ErrorKind.FORBIDDEN
        )


class WorkspaceConflict(AppException):
    def __init__(self, code: str = "WORKSPACE_CONFLICT") -> None:
        super().__init__(code, "현재 상태에서는 요청을 처리할 수 없습니다.", ErrorKind.CONFLICT)
