"""Application exception hierarchy + centralized FastAPI handlers.

Services raise these domain exceptions instead of ``HTTPException`` so business
logic stays framework-agnostic. The handlers registered in ``register_exception_handlers``
translate them into consistent JSON error responses at the API boundary.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base class for all expected application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, details: object | None = None) -> None:
        if message:
            self.message = message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    message = "Resource not found."


class AlreadyExistsError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "already_exists"
    message = "Resource already exists."


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"
    message = "Validation failed."


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"
    message = "Authentication failed."


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"
    message = "You do not have permission to perform this action."


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    message = "The request conflicts with the current state."


class BusinessRuleError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "business_rule_violation"
    message = "The operation violates a business rule."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )
