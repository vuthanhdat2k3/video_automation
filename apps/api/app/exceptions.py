from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = 500
    message: str = "Internal server error"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message


class NotFoundException(AppException):
    status_code = 404
    message = "Resource not found"


class ValidationException(AppException):
    status_code = 422
    message = "Validation error"


class ConflictException(AppException):
    status_code = 409
    message = "Conflict"


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"data": None, "error": {"code": exc.status_code, "message": exc.message}},
    )
