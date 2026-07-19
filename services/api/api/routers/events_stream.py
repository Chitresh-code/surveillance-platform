"""SSE forwarding of the real-time sighting feed (docs/DECISIONS.md ADR-0012).

Registered outside the `current_operator` header-based dependency every other
router uses: `EventSource` can't set an `Authorization` header, so the token
travels as a query param and is checked here instead.
"""

import os
from collections.abc import Iterator

import jwt
import redis
from common.events import SIGHTINGS_CHANNEL
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.auth import decode_access_token
from api.errors import APIError

router = APIRouter(tags=["events"])


def _stream() -> Iterator[str]:
    client = redis.Redis.from_url(os.environ["REDIS_URL"])
    pubsub = client.pubsub()
    pubsub.subscribe(SIGHTINGS_CHANNEL)
    try:
        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield f"data: {message['data'].decode()}\n\n"
    finally:
        pubsub.close()


@router.get("/events/stream")
def stream_sightings(token: str = Query(...)) -> StreamingResponse:
    try:
        decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise APIError(401, "unauthorized", "Invalid or expired token.") from exc
    return StreamingResponse(_stream(), media_type="text/event-stream")
