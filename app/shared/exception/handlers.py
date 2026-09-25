from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.shared.exception.base import AppException, ErrorKind


def error_response(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "trace_id": uuid4().hex}},
        status_code=status,
        headers={"Cache-Control": "private, no-store"},
    )


def register_handlers(app: FastAPI) -> None:
    async def domain_error(request: Request, exc: AppException) -> JSONResponse:
        status = {
            ErrorKind.UNAUTHORIZED: 401,
            ErrorKind.FORBIDDEN: 403,
            ErrorKind.INVALID_INPUT: 422,
            ErrorKind.UNAVAILABLE: 503,
        }[exc.kind]
        return error_response(exc.code, exc.public_message, status)

    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic errors may contain raw callback codes/tokens; never echo inputs.
        return error_response("INVALID_INPUT", "요청 형식을 확인해 주세요.", 422)

    async def unavailable(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        return error_response("DATABASE_UNAVAILABLE", "잠시 후 다시 시도해 주세요.", 503)

    app.add_exception_handler(AppException, domain_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, invalid_input)  # type: ignore[arg-type]
    app.add_exception_handler(SQLAlchemyError, unavailable)  # type: ignore[arg-type]
