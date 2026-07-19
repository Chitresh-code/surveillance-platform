"""REST API entrypoint (docs/API_SPEC.md). The only supported way to read/write platform state from outside."""

from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.deps import current_operator
from api.errors import APIError, api_error_handler, validation_error_handler
from api.routers import auth, cameras, events, identities, map as map_router, tracks

app = FastAPI(title="Surveillance Platform API")

# Wide open: bearer tokens (docs/DECISIONS.md ADR-0010) aren't sent automatically
# by the browser cross-origin the way cookies are, so an open allowlist here
# doesn't grant a CSRF path. Revisit if session cookies are ever added.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

API_V1 = "/api/v1"
app.include_router(auth.router, prefix=API_V1)

_protected = [Depends(current_operator)]
app.include_router(cameras.router, prefix=API_V1, dependencies=_protected)
app.include_router(tracks.router, prefix=API_V1, dependencies=_protected)
app.include_router(identities.router, prefix=API_V1, dependencies=_protected)
app.include_router(events.router, prefix=API_V1, dependencies=_protected)
app.include_router(map_router.router, prefix=API_V1, dependencies=_protected)
