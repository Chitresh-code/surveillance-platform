"""REST API entrypoint (docs/API_SPEC.md). The only supported way to read/write platform state from outside."""

import os

import redis
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.deps import current_operator, get_db, get_redis
from api.errors import APIError, api_error_handler, validation_error_handler
from api.routers import audit, auth, cameras, events, events_stream, identities, map as map_router, operators, tracks

app = FastAPI(title="Surveillance Platform API")


@app.get("/health", response_model=None)
def health(session: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)) -> dict | JSONResponse:
    """Unauthenticated liveness/readiness check (docs/GAPS.md item 8): a round-trip to
    every dependency the API actually needs to serve a request, not just the metadata
    store. Nothing versioned or resource-shaped here, so it lives outside /api/v1.
    """
    checks: dict[str, str] = {}

    try:
        session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unreachable"

    try:
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unreachable"

    frame_store_dir = os.environ.get("FRAME_STORE_DIR", "/data/frames")
    checks["frame_store"] = "ok" if os.path.isdir(frame_store_dir) else "unreachable"

    if all(status == "ok" for status in checks.values()):
        return {"status": "ok"}
    return JSONResponse(status_code=503, content={"status": "degraded", "checks": checks})

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
# Unprotected (query-param token auth, see api/routers/events_stream.py) and registered
# before events.router so its literal "/events/stream" path isn't shadowed by
# events.router's "/events/{event_id}".
app.include_router(events_stream.router, prefix=API_V1)

_protected = [Depends(current_operator)]
app.include_router(cameras.router, prefix=API_V1, dependencies=_protected)
app.include_router(tracks.router, prefix=API_V1, dependencies=_protected)
app.include_router(identities.router, prefix=API_V1, dependencies=_protected)
app.include_router(events.router, prefix=API_V1, dependencies=_protected)
app.include_router(map_router.router, prefix=API_V1, dependencies=_protected)
app.include_router(audit.router, prefix=API_V1, dependencies=_protected)
app.include_router(operators.router, prefix=API_V1, dependencies=_protected)
