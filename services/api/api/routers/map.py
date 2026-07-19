from common.models import Camera, Sighting
from common.pagination import DEFAULT_LIMIT, clamp_limit
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.pagination import paginate
from api.schemas import MapActivityListOut, MapCameraListOut

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/cameras", response_model=MapCameraListOut)
def list_map_cameras(limit: int = DEFAULT_LIMIT, cursor: str | None = None, session: Session = Depends(get_db)) -> dict:
    rows, next_cursor = paginate(session, select(Camera), Camera, Camera.created_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}


@router.get("/activity", response_model=MapActivityListOut)
def list_map_activity(limit: int = 100, session: Session = Depends(get_db)) -> dict:
    # ponytail: recent-N snapshot for a live overlay, not cursor-paged like /events,
    # which already covers the paged historical query.
    stmt = (
        select(Sighting.id, Sighting.identity_id, Sighting.camera_id, Sighting.seen_at, Camera.lat, Camera.lon)
        .join(Camera, Camera.id == Sighting.camera_id)
        .order_by(Sighting.seen_at.desc())
        .limit(clamp_limit(limit))
    )
    rows = session.execute(stmt).all()
    return {"data": [row._mapping for row in rows]}
