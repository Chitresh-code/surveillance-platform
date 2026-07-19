"""REST API entrypoint (docs/API_SPEC.md). The only supported way to read/write platform state from outside."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api.errors import APIError, api_error_handler, validation_error_handler
from api.routers import cameras, identities, tracks

app = FastAPI(title="Surveillance Platform API")

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

API_V1 = "/api/v1"
app.include_router(cameras.router, prefix=API_V1)
app.include_router(tracks.router, prefix=API_V1)
app.include_router(identities.router, prefix=API_V1)
