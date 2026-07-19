from common.models import Detection, Track
from common.pagination import DEFAULT_LIMIT
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import APIError
from api.pagination import paginate
from api.schemas import DetectionListOut, TrackOut

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/{track_id}", response_model=TrackOut)
def get_track(track_id: str, session: Session = Depends(get_db)) -> Track:
    track = session.get(Track, track_id)
    if track is None:
        raise APIError(404, "track_not_found", f"No track with id {track_id}.")
    return track


@router.get("/{track_id}/detections", response_model=DetectionListOut)
def list_track_detections(
    track_id: str, limit: int = DEFAULT_LIMIT, cursor: str | None = None, session: Session = Depends(get_db)
) -> dict:
    if session.get(Track, track_id) is None:
        raise APIError(404, "track_not_found", f"No track with id {track_id}.")
    stmt = select(Detection).where(Detection.track_id == track_id)
    rows, next_cursor = paginate(session, stmt, Detection, Detection.captured_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}
