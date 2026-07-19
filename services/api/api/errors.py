"""Error envelope (docs/API_SPEC.md §5): {"error": {"code": ..., "message": ...}}."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def _envelope(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_envelope(exc.code, exc.message))


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content=_envelope("validation_error", str(exc.errors())))
