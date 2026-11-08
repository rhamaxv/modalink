from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.utils import is_body_allowed_for_status_code
from starlette.exceptions import HTTPException as StarletteHTTPException


class DomainError(Exception):
    status = 400

    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail or {}


class NotFoundError(DomainError):
    status = 404


class ForbiddenError(DomainError):
    status = 403


class ConflictError(DomainError):
    """Transisi status tidak sah, atau aturan bisnis dilanggar."""

    status = 409


class UnprocessableError(DomainError):
    status = 422


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "payload_tidak_valid",
                    "message": "Data yang dikirim tidak valid.",
                    "detail": {"errors": jsonable_encoder(exc.errors())},
                }
            },
        )

    # Starlette raises its own HTTPException for routing failures (404, 405, ...)
    # that never reach application code, so this has to catch the base class
    # rather than only fastapi.HTTPException.
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> Response:
        # Mirrors fastapi's own http_exception_handler: a caller-supplied
        # header (e.g. WWW-Authenticate on a 401) must survive, and 204/304/1xx
        # responses are illegal with a body.
        if not is_body_allowed_for_status_code(exc.status_code):
            return Response(status_code=exc.status_code, headers=exc.headers)
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": "kesalahan_permintaan",
                    "message": str(exc.detail),
                    "detail": {},
                }
            },
        )
