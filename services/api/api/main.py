"""REST API entrypoint (docs/API_SPEC.md). The only supported way to read/write platform state from outside."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.errors import APIError, api_error_handler, validation_error_handler
from api.routers import cameras, events, identities, map as map_router, tracks

app = FastAPI(title="Surveillance Platform API")

# Wide open until auth (docs/API_SPEC.md §7 open item) lands; the Map UI is a
# browser client on its own origin (docs/ARCHITECTURE.md: "a client of the REST
# API, nothing more"), so it needs CORS at all, and there's no session/cookie to
# scope an allowlist to yet.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

API_V1 = "/api/v1"
app.include_router(cameras.router, prefix=API_V1)
app.include_router(tracks.router, prefix=API_V1)
app.include_router(identities.router, prefix=API_V1)
app.include_router(events.router, prefix=API_V1)
app.include_router(map_router.router, prefix=API_V1)
