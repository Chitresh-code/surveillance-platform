from datetime import datetime

from common.models import Sighting
from common.pagination import DEFAULT_LIMIT
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import APIError
from api.pagination import paginate
from api.schemas import EventListOut, EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=EventListOut)
def list_events(
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    camera_id: str | None = None,
    identity_id: str | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    session: Session = Depends(get_db),
) -> dict:
    stmt = select(Sighting)
    if camera_id is not None:
        stmt = stmt.where(Sighting.camera_id == camera_id)
    if identity_id is not None:
        stmt = stmt.where(Sighting.identity_id == identity_id)
    if from_ is not None:
        stmt = stmt.where(Sighting.seen_at >= from_)
    if to is not None:
        stmt = stmt.where(Sighting.seen_at <= to)
    rows, next_cursor = paginate(session, stmt, Sighting, Sighting.seen_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: str, session: Session = Depends(get_db)) -> Sighting:
    event = session.get(Sighting, event_id)
    if event is None:
        raise APIError(404, "event_not_found", f"No event with id {event_id}.")
    return event
